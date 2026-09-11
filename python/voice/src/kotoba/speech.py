"""Local ASR with explicit language selection and reviewable uncertainty."""

from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path
from time import perf_counter
from typing import Callable, Protocol

import numpy as np
from .dictation import dictionary_echo
from .speech_models import resolve_model, PARAKEET_MODELS, JAPANESE_MODEL, prepare_parakeet, ParakeetRecognizer, ModelDownloadRequired


@dataclass(frozen=True)
class SpeechConfig:
    model: str = "auto"
    language: str = "ja"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    glossary: str = ""
    max_seconds: float = 120
    review_logprob: float = -0.7
    min_rms: float = 0.001
    context: str = "dictation"
    processing: str = "local"

    def __post_init__(self):
        if self.language not in {"ja", "en", "auto"}:
            raise ValueError("Choose ja, en, or auto.")
        if self.device not in {"cpu", "cuda"} or self.beam_size < 1:
            raise ValueError("Invalid inference configuration.")
        if not 0 < self.max_seconds <= 600 or not 0 <= self.min_rms < 1:
            raise ValueError("Invalid audio limits.")
        if len(self.glossary) > 1000:
            raise ValueError("Glossary is limited to 1,000 characters.")
        if self.context not in {"dictation", "meeting"}:
            raise ValueError("Invalid speech context")
        if self.processing not in {"local", "cloud"}:
            raise ValueError("Invalid processing mode")


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str
    avg_logprob: float | None
    no_speech_probability: float | None


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    language_probability: float
    segments: tuple[Segment, ...]
    duration_seconds: float
    latency_seconds: float
    model: str
    review_reasons: tuple[str, ...]

    @property
    def real_time_factor(self) -> float:
        return self.latency_seconds / max(self.duration_seconds, 0.001)

    def to_dict(self) -> dict:
        return asdict(self)


class Recognizer(Protocol):
    def transcribe(self, audio, **kwargs): ...


class SpeechEngine:
    """Cache one local model; callers serialize inference on a worker thread."""

    def __init__(self, cache: Path, factory: Callable | None = None):
        self.cache = cache
        self.factory = factory
        self._model: Recognizer | None = None
        self._key = None
        self.cloud = None

    def prepare(self, config: SpeechConfig, allow_download=True, progress=None):
        from .model_progress import ModelProgress, download_whisper
        if progress:
            progress(ModelProgress("checking"))
        if config.processing == "cloud":
            if self.cloud is None:
                raise RuntimeError("Configure cloud speech in Audio settings first. / 音声設定でクラウドを設定してください。")
            return
        config = replace(config, model=resolve_model(config.model, config.language))
        key = (config.model, config.device, config.compute_type)
        if key != self._key:
            factory = self.factory
            self._model = None
            self._key = None
            if factory is None and config.model in PARAKEET_MODELS:
                path = prepare_parakeet(self.cache, config.model, allow_download, progress)
                if progress:
                    progress(ModelProgress("loading"))
                self._model = ParakeetRecognizer(path)
                self._key = key
                return
            if factory is None:
                from faster_whisper import WhisperModel
                from faster_whisper.utils import download_model
                factory = WhisperModel
                from huggingface_hub.errors import LocalEntryNotFoundError
                try:
                    if Path(config.model).is_dir():
                        model_path = Path(config.model)
                    elif progress:
                        model_path = Path(download_whisper(config.model, self.cache, allow_download, progress))
                    else:
                        model_path = Path(download_model(config.model, cache_dir=str(self.cache),
                                                         local_files_only=not allow_download))
                except LocalEntryNotFoundError as error:
                    raise ModelDownloadRequired(config.model) from error
                # faster-whisper otherwise fetches a fallback tokenizer even in
                # local_files_only mode; incomplete local models must fail offline.
                if not (model_path / "tokenizer.json").is_file():
                    raise ModelDownloadRequired(config.model)
                model_name = str(model_path)
            else:
                model_name = config.model
            if progress:
                progress(ModelProgress("loading"))
            self._model = factory(model_name, device=config.device,
                                  compute_type=config.compute_type, download_root=str(self.cache),
                                  local_files_only=not allow_download)
            self._key = key

    def transcribe(self, audio: np.ndarray, config: SpeechConfig) -> Transcript:
        """Accept mono 16 kHz float PCM; never translate or silently rewrite it."""
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
            raise ValueError("Audio must be finite, nonempty mono PCM at 16 kHz.")
        duration = len(audio) / 16000
        if duration > config.max_seconds:
            raise ValueError(f"Audio exceeds the {config.max_seconds:g} second limit.")
        if np.max(np.abs(audio)) > 1.01:
            raise ValueError("PCM amplitude must be between -1 and 1.")
        start = perf_counter()
        if float(np.sqrt(np.mean(audio ** 2))) < config.min_rms:
            return Transcript("", config.language, 0, (), duration, perf_counter() - start,
                              config.model, ("no_speech",))
        if config.processing == "cloud":
            self.prepare(config, allow_download=False)
            return self.cloud.transcribe(audio, config)
        config = replace(config, model=resolve_model(config.model, config.language))
        self.prepare(config, allow_download=False)
        segments, info = self._model.transcribe(
            audio, language=None if config.language == "auto" else config.language,
            task="transcribe", beam_size=config.beam_size, temperature=0.0,
            # OpenWhispr whisperVadConfig.js: preserve pauses in dictation;
            # Silero is enabled for long-form meetings, where silence dominates.
            vad_filter=config.context == "meeting", vad_parameters={"min_silence_duration_ms": 500},
            # The distilled two-layer Japanese model has no compatible alignment
            # heads for CTranslate2 word alignment. Keep its segment timestamps.
            condition_on_previous_text=False, word_timestamps=config.model != JAPANESE_MODEL,
            hotwords=config.glossary or None,
            chunk_length=15 if config.model == JAPANESE_MODEL else 30,
        )
        kept = tuple(Segment(s.start, s.end, s.text, s.avg_logprob, s.no_speech_prob)
                     for s in segments)
        text = "".join(s.text for s in kept).strip()
        reasons = []
        if not text:
            reasons.append("no_speech")
        if info.language not in {"ja", "en"}:
            reasons.append("unsupported_language")
        if config.language == "auto" and info.language_probability < 0.8:
            reasons.append("language_uncertain")
        if any(s.avg_logprob is not None and (not math.isfinite(s.avg_logprob) or s.avg_logprob < config.review_logprob) for s in kept):
            reasons.append("low_decoder_score")
        if any(s.no_speech_probability is not None and s.no_speech_probability > 0.6 for s in kept):
            reasons.append("possible_non_speech")
        if float(np.mean(np.abs(audio) >= 0.99)) > 0.01:
            reasons.append("clipping")
        if config.glossary and dictionary_echo(text, config.glossary):
            reasons.append("possible_dictionary_echo")
        return Transcript(text, info.language, info.language_probability, kept, duration,
                          perf_counter() - start, config.model, tuple(reasons))


def load_audio(path: str, max_seconds: float = 120) -> np.ndarray:
    """Decode locally and bound decoded duration before ASR; audio is never uploaded."""
    import av
    chunks = []
    samples = 0
    with av.open(path) as container:
        resampler = av.audio.resampler.AudioResampler(format="fltp", layout="mono", rate=16000)
        for frame in container.decode(audio=0):
            for output in resampler.resample(frame):
                chunk = output.to_ndarray().reshape(-1)
                samples += len(chunk)
                if samples > max_seconds * 16000:
                    raise ValueError(f"Audio exceeds the {max_seconds:g} second limit.")
                chunks.append(chunk)
        for output in resampler.resample(None):
            chunks.append(output.to_ndarray().reshape(-1))
    audio = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
    if len(audio) > max_seconds * 16000:
        raise ValueError("Decoded audio exceeds duration limit.")
    # Lossy codecs can reconstruct peaks outside the PCM range; clip before inference.
    return np.clip(audio, -1.0, 1.0)
