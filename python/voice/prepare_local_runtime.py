"""Download and verify the pinned CPU engine for Windows packaging; no model weights."""

import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile


def main():
    voice = Path(__file__).resolve().parent
    manifest = json.loads((voice / "native/llama-runtime.json").read_text())
    with urllib.request.urlopen(manifest["url"], timeout=60) as response:
        data = response.read(100_000_001)
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise RuntimeError("llama.cpp archive checksum does not match the pinned release")
    output = voice.parents[1] / "dist-exe/llama"
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            # Copy only flat runtime files; archive paths never become filesystem targets.
            if "/" in entry.filename or "\\" in entry.filename:
                raise RuntimeError("Unexpected nested runtime archive")
            if entry.filename == "llama-server.exe" or entry.filename.endswith(".dll") or entry.filename.startswith("LICENSE"):
                (output / entry.filename).write_bytes(archive.read(entry))
    (output / "runtime.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
