import hashlib
import io
import tarfile

import pytest

from kotoba.model_progress import ModelProgress, download_whisper
from kotoba import speech_models


@pytest.mark.parametrize("known_size", [False, True])
def test_parakeet_reports_received_bytes_then_extracts_atomically(tmp_path, monkeypatch, known_size):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w:bz2") as archive:
        for name in ("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt"):
            member = tarfile.TarInfo(f"fixture/{name}")
            member.size = 4
            archive.addfile(member, io.BytesIO(b"test"))
    payload = data.getvalue()
    response = io.BytesIO(payload)
    response.headers = {"Content-Length": str(len(payload))} if known_size else {}
    monkeypatch.setitem(speech_models.PARAKEET_MODELS, "fixture", ("fixture", hashlib.sha256(payload).hexdigest()))
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: response)
    events = []
    target = speech_models.prepare_parakeet(tmp_path, "fixture", True, events.append)
    assert events == [ModelProgress("downloading", len(payload), len(payload) if known_size else 0),
                      ModelProgress("extracting")]
    assert (target / "tokens.txt").read_bytes() == b"test"
    assert not list(tmp_path.glob("speech-download-*"))
    events.clear()
    speech_models.prepare_parakeet(tmp_path, "fixture", False, events.append)
    assert events == []


def test_whisper_progress_uses_hub_callback_without_global_patches(tmp_path, monkeypatch):
    calls = []
    def snapshot(repo, **kwargs):
        calls.append((repo, kwargs))
        cls = kwargs["tqdm_class"]
        with cls(total=200, unit="B", mininterval=0) as bar:
            bar.update(100)
            bar.update(100)
        return str(tmp_path)
    monkeypatch.setattr("huggingface_hub.snapshot_download", snapshot)
    events = []
    assert download_whisper("base", tmp_path, True, events.append) == str(tmp_path)
    assert calls[0][0] == "Systran/faster-whisper-base"
    assert calls[0][1]["local_files_only"] is False
    assert ModelProgress("downloading", 100, 200) in events
    assert events[-1] == ModelProgress("downloading", 200, 200)
