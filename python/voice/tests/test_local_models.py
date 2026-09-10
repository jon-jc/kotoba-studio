import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest

from kotoba.local_models import local_endpoint, model_arguments, provider_profile, discover_models, HarnessRemote


@pytest.mark.parametrize("value", ["https://example.com/v1", "http://example.com:80/v1", "http://127.0.0.1.evil:80/v1",
    "http://u:p@127.0.0.1:80/v1", "http://127.0.0.1:80/v1?key=x", "http://localhost/v1", "http://localhost:80/other"])
def test_local_mode_rejects_nonlocal_or_ambiguous_destinations(value):
    with pytest.raises(ValueError):
        local_endpoint(value)


def test_local_endpoint_and_native_start_arguments(tmp_path):
    assert local_endpoint("http://127.0.0.1:11434/") == "http://127.0.0.1:11434/v1"
    assert local_endpoint("http://[::1]:1234/v1/") == "http://[::1]:1234/v1"
    file = tmp_path / "日本語 model.gguf"
    file.write_bytes(b"GGUF" + b"\0" * 20)
    args = model_arguments(file, 12345, 16384)
    assert args[args.index("--model") + 1] == str(file.resolve())
    assert args[args.index("--host") + 1] == "127.0.0.1"
    assert "--no-webui" in args and "--jinja" in args
    assert "--reasoning-budget" not in args  # Zero can terminate before any visible output.
    file.write_bytes(b"not a model")
    with pytest.raises(ValueError):
        model_arguments(file, 12345, 16384)


def test_local_profile_has_explicit_context_and_no_automatic_retries():
    profile = provider_profile("http://localhost:1234/v1", "qwen-local", 16384, "LOCAL_KEY")
    assert profile["models"][0]["contextWindow"] == 16384
    assert profile["retryPolicy"]["maxRetries"] == 0
    assert profile["apiKeyEnv"] == "LOCAL_KEY"
    assert profile["baseURL"] == "http://localhost:1234/v1"


@pytest.fixture
def server():
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path == "/v1/models":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"data": [{"id": "qwen-local"}]}).encode())
            else:
                self.send_response(302 if "?token=" in self.path else 200)
                if "?token=" in self.path:
                    self.send_header("Location", "/")
                self.send_header("Set-Cookie", "test=owned; HttpOnly; SameSite=Strict")
                self.end_headers()
        def do_POST(self):
            assert self.headers.get("Cookie") == "test=owned"
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(data)
            value = {"namespaces": [{"ns": "llm-pi-ai", "revision": 7}]} if self.path.endswith("describe") else {}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"result": {"ok": True, "value": value}}).encode())
    host = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=host.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{host.server_port}", calls
    host.shutdown()
    host.server_close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_discovery_and_owned_provider_registration_preserve_other_routes(server):
    url, calls = server
    assert discover_models(url) == ["qwen-local"]
    assert HarnessRemote(url + "/?token=test").register_local(url, "qwen-local", 8192, "local-key") == "kotoba-local"
    assert [call["method"] for call in calls] == ["settings/describe", "credentials/set", "settings/mutate"]
    mutation = calls[-1]["payload"]["args"]
    assert mutation["expectedRevision"] == 7
    assert mutation["ops"][0]["path"] == ["providers", "kotoba-local"]
    assert "local-key" not in json.dumps(mutation)


def test_local_session_never_uses_cloud_key_or_retries_failed_turn(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from kotoba.harness import HarnessSession
    configs, calls = [], []
    class Client:
        def __init__(self, **config):
            configs.append(config)
        def run(self, text, **kwargs):
            calls.append(text)
            raise ConnectionError("local engine stopped")
        def close(self):
            pass
    monkeypatch.setattr("deepseek_harness.DeepSeekHarness", Client)
    monkeypatch.setattr("kotoba.harness.runtime_path", lambda: tmp_path / "runtime.exe")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "cloud-secret")
    session = HarnessSession(tmp_path)
    with pytest.raises(ConnectionError, match="local engine stopped"):
        session.run("こんにちは", str(tmp_path), "local-model", "session-cloud-secret", lambda _: None, provider="kotoba-local")
    assert calls == ["こんにちは"]
    assert configs[0]["api_key"] is None
    assert configs[0]["profile"] == "sdk"
    assert configs[0]["provider"] == "kotoba-local"
    assert session.client is None


def test_incomplete_local_output_is_not_reported_as_success(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from kotoba.harness import HarnessSession
    class Client:
        def __init__(self, **config):
            pass
        def run(self, *args, **kwargs):
            return SimpleNamespace(finish_reason="max-tokens", final_response="partial")
        def close(self):
            pass
    monkeypatch.setattr("deepseek_harness.DeepSeekHarness", Client)
    monkeypatch.setattr("kotoba.harness.runtime_path", lambda: tmp_path / "runtime.exe")
    session = HarnessSession(tmp_path)
    try:
        with pytest.raises(RuntimeError, match="max-tokens"):
            session.run("hello", str(tmp_path), "local-model", "", lambda _: None, provider="kotoba-local")
    finally:
        session.close()
