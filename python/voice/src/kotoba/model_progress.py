"""Per-download progress callbacks; no global hooks or terminal output."""

from dataclasses import dataclass
from io import StringIO
from threading import RLock


@dataclass(frozen=True)
class ModelProgress:
    phase: str
    completed: int = 0
    total: int = 0
    unit: str = "bytes"


def download_whisper(model, cache, allow_download, report):
    """Reuse the pinned faster-whisper registry and Hugging Face cache/downloads."""
    from faster_whisper.utils import _MODELS
    from huggingface_hub import snapshot_download
    from huggingface_hub.utils import tqdm as HubTqdm
    from tqdm.auto import tqdm

    repo = model if "/" in model else _MODELS.get(model)
    if repo is None:
        raise ValueError(f"Unknown Whisper model: {model}")
    bytes_seen = False

    class DownloadProgress(HubTqdm):
        _lock = RLock()

        def __init__(self, *args, **kwargs):
            self.transfer_only = (kwargs.pop("name", "") or "").endswith(".transfer")
            kwargs["disable"] = False
            kwargs["file"] = StringIO()
            # Console suppression must not suppress the application's own progress.
            tqdm.__init__(self, *args, **kwargs)

        def display(self, *args, **kwargs):
            nonlocal bytes_seen
            if self.transfer_only:
                return
            is_bytes = self.unit == "B"
            bytes_seen = bytes_seen or is_bytes
            if is_bytes or not bytes_seen:
                report(ModelProgress("downloading", int(self.n), int(self.total or 0),
                                     "bytes" if is_bytes else "files"))

    return snapshot_download(repo, cache_dir=str(cache), local_files_only=not allow_download,
        allow_patterns=["config.json", "preprocessor_config.json", "model.bin",
                        "tokenizer.json", "vocabulary.*"], tqdm_class=DownloadProgress)
