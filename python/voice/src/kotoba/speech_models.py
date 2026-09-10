"""OpenWhispr model registry and sherpa-onnx adapter, adapted for Python (MIT).

Registry/file layout from src/models/modelRegistryData.json and
src/helpers/parakeetModelInfo.js at c6a871db1b8ada646eb728d3592431ecc8c17723.
Copyright (c) 2024 OpenWhispr Team; see THIRD_PARTY_LICENSES/OpenWhispr.txt.
"""

import hashlib
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
from types import SimpleNamespace
import urllib.request

JAPANESE_MODEL = "kotoba-tech/kotoba-whisper-v2.0-faster"
PARAKEET_MODELS = {
    "parakeet-unified-en-0.6b": (
        "sherpa-onnx-nemo-parakeet-unified-en-0.6b-int8-non-streaming",
        "99f63605b3a85a54c250c0869670a687b7d6598a47bf2421515e1f839a76e150"),
    "parakeet-tdt-0.6b-v3": (
        "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8",
        "5793d0fd397c5778d2cf2126994d58e9d56b1be7c04d13c7a15bb1b4eafb16bf"),
}
MODEL_CHOICES = (
    ("auto", "Recommended by language", "言語別の推奨モデル"),
    ("parakeet-unified-en-0.6b", "Parakeet Unified · English · CPU", "Parakeet Unified · 英語 · CPU"),
    ("parakeet-tdt-0.6b-v3", "Parakeet v3 · English · CPU", "Parakeet v3 · 英語 · CPU"),
    (JAPANESE_MODEL, "Kotoba-Whisper v2 · Japanese", "Kotoba-Whisper v2 · 日本語"),
    ("large-v3", "Whisper large-v3 · quality", "Whisper large-v3 · 精度重視"),
    ("turbo", "Whisper Turbo · bilingual", "Whisper Turbo · 日英対応"),
    ("small", "Whisper small · lighter CPU", "Whisper small · 軽量 CPU"),
    ("base", "Whisper base · lowest memory", "Whisper base · 省メモリ"),
)


def resolve_model(model, language):
    if model == "auto":
        return "parakeet-unified-en-0.6b" if language == "en" else JAPANESE_MODEL if language == "ja" else "turbo"
    if model in PARAKEET_MODELS and language != "en":
        raise ValueError("Select English for Parakeet; use Whisper for Japanese or automatic language detection. / Parakeet は英語を選択してください。")
    if model == JAPANESE_MODEL and language != "ja":
        raise ValueError("Kotoba-Whisper requires Japanese. / Kotoba-Whisper は日本語専用です。")
    return model


def prepare_parakeet(cache: Path, model: str, allow_download: bool):
    directory, digest = PARAKEET_MODELS[model]
    target = cache / directory
    required = ("encoder.int8.onnx", "decoder.int8.onnx", "joiner.int8.onnx", "tokens.txt")
    if all((target / name).is_file() for name in required):
        return target
    if not allow_download:
        raise RuntimeError("Download this speech model in Audio settings first. / 音声設定でモデルを準備してください。")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="speech-download-", dir=cache) as temporary:
        stage = Path(temporary)
        archive = stage / "model.tar.bz2"
        url = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{directory}.tar.bz2"
        checksum = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 900_000_000:
                    raise ValueError("Speech model exceeds download size limit")
                output.write(chunk)
                checksum.update(chunk)
        if checksum.hexdigest() != digest:
            raise ValueError("Speech model checksum mismatch")
        extracted = stage / "ready"
        extracted.mkdir()
        with tarfile.open(archive) as bundle:
            for name in required:
                member = bundle.getmember(f"{directory}/{name}")
                if not member.isfile() or member.size > 1_500_000_000:
                    raise ValueError("Invalid speech model archive")
                with bundle.extractfile(member) as source, (extracted / name).open("wb") as output:
                    shutil.copyfileobj(source, output)
        if target.exists():
            raise RuntimeError("An incomplete model directory exists; select another cache or remove that directory.")
        extracted.rename(target)
    return target


class ParakeetRecognizer:
    def __init__(self, path):
        import sherpa_onnx
        self.model = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(path / "encoder.int8.onnx"), decoder=str(path / "decoder.int8.onnx"),
            joiner=str(path / "joiner.int8.onnx"), tokens=str(path / "tokens.txt"),
            num_threads=max(1, min(4, (os.cpu_count() or 2) // 2)), model_type="nemo_transducer", provider="cpu")

    def transcribe(self, audio, **kwargs):
        stream = self.model.create_stream()
        stream.accept_waveform(16000, audio)
        self.model.decode_stream(stream)
        text = stream.result.text.strip()
        # Sherpa exposes token timestamps but no calibrated decoder confidence.
        rows = [SimpleNamespace(start=0, end=len(audio) / 16000, text=text,
                                avg_logprob=None, no_speech_prob=None)] if text else []
        return rows, SimpleNamespace(language="en", language_probability=1.0)
