"""Local model endpoints and registration through the existing Harness settings API."""

import http.cookiejar
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Local model endpoints must not redirect. / ローカル接続のリダイレクトは禁止です。")


class OwnedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin):
        super().__init__()
        self.origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if (f"{parsed.scheme}://{parsed.netloc}" != self.origin):
            raise ValueError("Runtime authentication redirected outside its owned origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def local_endpoint(value: str) -> str:
    """Accept only literal loopback destinations; do not resolve arbitrary hostnames."""
    parsed = urllib.parse.urlsplit(value.strip())
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Use a loopback HTTP endpoint, e.g. http://127.0.0.1:11434/v1 / ローカルの HTTP 接続先を指定してください。")
    if parsed.port is None or not 1 <= parsed.port <= 65535:
        raise ValueError("Specify the local server port. / ポート番号を指定してください。")
    path = parsed.path.rstrip("/")
    if path not in ("", "/v1"):
        raise ValueError("Use the server's /v1 endpoint. / /v1 を指定してください。")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/v1", "", ""))


def local_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def discover_models(endpoint: str, key: str = "") -> list[str]:
    request = urllib.request.Request(local_endpoint(endpoint) + "/models")
    if key:
        request.add_header("Authorization", "Bearer " + key)
    with local_opener().open(request, timeout=3) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("Model list is too large.")
    data = json.loads(payload)
    models = data.get("data") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise ValueError("The server did not return a model list. / モデル一覧を取得できませんでした。")
    result = [item["id"] for item in models if isinstance(item, dict) and isinstance(item.get("id"), str)
              and 0 < len(item["id"]) <= 512]
    if not result:
        raise ValueError("No loaded models. Load a model in the local server first. / サーバーでモデルを読み込んでください。")
    return list(dict.fromkeys(result))


def llama_path() -> Path:
    root = Path(sys.executable).parent / "runtime" if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[4] / "dist-exe"
    path = root / "llama" / "llama-server.exe"
    if not path.is_file():
        raise FileNotFoundError("Bundled local-model engine is missing. Reinstall Kotoba Studio. / ローカル推論エンジンが見つかりません。")
    return path


def model_arguments(model: Path, port: int, context: int) -> list[str]:
    model = model.resolve(strict=True)
    if model.suffix.lower() != ".gguf":
        raise ValueError("Choose a GGUF model file. / GGUF モデルを選択してください。")
    with model.open("rb") as file:
        if file.read(4) != b"GGUF":
            raise ValueError("This file is not GGUF. / GGUF ファイルではありません。")
    if not 1024 <= context <= 131072 or not 1 <= port <= 65535:
        raise ValueError("Invalid context or port.")
    return ["--model", str(model), "--host", "127.0.0.1", "--port", str(port), "--ctx-size", str(context),
            "--parallel", "1", "--gpu-layers", "0", "--alias", "kotoba-local", "--jinja", "--no-webui",
            "--chat-template-kwargs", '{"enable_thinking":false}']


def provider_profile(endpoint: str, model: str, context: int, key_ref: str) -> dict:
    if not model or len(model) > 512 or not 1024 <= context <= 131072:
        raise ValueError("Invalid local model or context size.")
    return {"displayName": "Kotoba Local", "api": "openai-completions", "baseURL": local_endpoint(endpoint),
            "apiKeyEnv": key_ref, "models": [{"id": model, "name": model, "contextWindow": context,
                "maxTokens": min(2048, context // 4), "reasoningEfforts": False}],
            "compat": {"supportsStore": False, "supportsDeveloperRole": False, "maxTokensField": "max_tokens"},
            "retryPolicy": {"mode": "normal", "maxRetries": 0}}


class HarnessRemote:
    """Authenticated loopback client for the desktop-owned Harness backend."""
    def __init__(self, url: str):
        parsed = urllib.parse.urlsplit(url)
        self.origin = f"http://127.0.0.1:{parsed.port}"
        if parsed.hostname != "127.0.0.1" or parsed.scheme != "http" or parsed.port is None:
            raise ValueError("Invalid owned runtime URL")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), OwnedRedirect(self.origin),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener.open(url, timeout=10).close()

    def call(self, method: str, args: dict):
        request = urllib.request.Request(self.origin + "/api/" + method, method="POST",
            headers={"Content-Type": "application/json", "Origin": self.origin},
            data=json.dumps({"type": "client-request", "rpcId": uuid.uuid4().hex, "method": method,
                             "payload": {"args": args}}).encode())
        with self.opener.open(request, timeout=15) as response:
            result = json.load(response)["result"]
        if not result.get("ok"):
            raise RuntimeError(result.get("error", {}).get("message", "Local route configuration failed"))
        return result.get("value")

    def register_local(self, endpoint: str, model: str, context: int, key: str) -> str:
        """Update only the Kotoba-owned route, preserving other providers and using revisions."""
        key_ref = "KOTOBA_LOCAL_MODEL_" + uuid.uuid4().hex.upper()
        profile = provider_profile(endpoint, model, context, key_ref)
        view = self.call("settings/describe", {})
        namespace = next(item for item in view["namespaces"] if item["ns"] == "llm-pi-ai")
        self.call("credentials/set", {"ref": key_ref, "value": key or "local-no-key"})
        self.call("settings/mutate", {"ns": "llm-pi-ai", "ops": [
            {"op": "set", "path": ["providers", "kotoba-local"], "value": profile}],
            "expectedRevision": namespace["revision"]})
        return "kotoba-local"
