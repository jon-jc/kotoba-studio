"""Same-checkout SDK adapter; no replacement agent loop or automatic turn retry."""

from pathlib import Path
import os
import sys
import uuid


def runtime_path() -> Path:
    if getattr(sys, "frozen", False):
        path = Path(sys.executable).parent / "runtime" / "deepseek-harness-sdk-runtime-win-x64.exe"
    else:
        root = Path(__file__).resolve().parents[4]
        native = root / "dist-exe" / "deepseek-harness-sdk-runtime-win-x64.exe"
        path = native if native.is_file() else root / "apps" / "cli" / "lib" / "bin.js"
    if not path.is_file():
        raise FileNotFoundError("Matching Harness runtime missing. Build the checkout or reinstall Kotoba.")
    return path


class HarnessSession:
    def __init__(self, home: Path):
        self.home = home
        self.session_id = "kotoba-" + uuid.uuid4().hex
        self.client = None
        self.identity = None

    def run(self, text: str, workspace: str, model: str, api_key: str, notify, provider="deepseek-official"):
        if not text.strip():
            raise ValueError("Review and enter a transcript first.")
        if not Path(workspace).is_dir():
            raise ValueError("Select an existing workspace directory.")
        if provider not in ("deepseek-official", "kotoba-local"):
            raise ValueError("Select a configured cloud or local provider.")
        identity = (str(Path(workspace).resolve()), model, api_key if provider == "deepseek-official" else "", provider)
        if identity != self.identity:
            self.close()
            from deepseek_harness import DeepSeekHarness
            self.client = DeepSeekHarness(
                dsh_bin=str(runtime_path()), dsh_home=str(self.home), cwd=identity[0],
                profile="sdk", provider=provider, model=model,
                api_key=(api_key or os.environ.get("DEEPSEEK_API_KEY")) if provider == "deepseek-official" else None,
                max_tokens=1024 if provider == "kotoba-local" else None,
                request_timeout_seconds=600 if provider == "kotoba-local" else 180, initialize_timeout_seconds=60,
                env={"DSH_TELEMETRY_DISABLED": "1", "DSH_MAX_TOKENS_AS_SUCCESS": "false"},
            )
            self.identity = identity
            self.session_id = "kotoba-" + uuid.uuid4().hex
        try:
            result = self.client.run(text, session_id=self.session_id, on_notification=notify)
        except Exception:
            self.close()
            raise
        if result.finish_reason != "completed":
            raise RuntimeError(f"Harness stopped with {result.finish_reason!r}. Inspect the session before retrying; tools may already have run.")
        return result

    def close(self):
        if self.client is not None:
            self.client.close()
        self.client = None
        self.identity = None
