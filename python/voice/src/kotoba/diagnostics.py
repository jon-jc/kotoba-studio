"""Opt-in, local distribution checks. Reports never include recognized text or keys."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from .audio_sources import helper_path
from .harness import runtime_path
from .local_models import llama_path
from .speech import SpeechEngine, SpeechConfig, load_audio


def main():
    report = {"ok": False}
    output = Path(os.environ["KOTOBA_VERIFY_REPORT"])
    try:
        import av
        import ctranslate2
        import sounddevice
        from deepseek_harness import DeepSeekHarness
        from PySide6.QtCore import qVersion
        report["qt"] = qVersion()
        report["ctranslate2"] = ctranslate2.__version__
        report["av"] = av.__version__
        report["harness_runtime_exists"] = runtime_path().is_file()
        local = subprocess.run([str(llama_path()), "--version"], capture_output=True, text=True,
                               timeout=15, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        report["local_engine"] = (local.stdout + local.stderr).strip()[:500]
        helper = subprocess.run([str(helper_path()), "probe"], capture_output=True, text=True,
                                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        report["capture"] = json.loads(helper.stdout)
        with tempfile.TemporaryDirectory(prefix="kotoba-check-") as folder:
            engine = SpeechEngine(Path(folder))
            model = os.environ.get("KOTOBA_VERIFY_MODEL")
            audio = os.environ.get("KOTOBA_VERIFY_AUDIO")
            config = SpeechConfig(model=model or "large-v3", language=os.environ.get("KOTOBA_VERIFY_LANGUAGE", "ja"))
            result = engine.transcribe(load_audio(audio, 120) if audio else np.zeros(16000, dtype=np.float32), config)
            report["audio_seconds"] = result.duration_seconds
            report["text_characters"] = len(result.text)
            report["latency_seconds"] = result.latency_seconds
        report["ok"] = True
    except Exception as error:
        report["error_type"] = type(error).__name__
        raise
    finally:
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
