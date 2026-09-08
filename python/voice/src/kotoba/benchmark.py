"""Run timestamped local recordings; keep transcripts and reference text private."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import av
import numpy as np
from .speech import SpeechConfig, SpeechEngine
from .evaluate import score


def excerpt(path: Path, start: float, end: float) -> np.ndarray:
    if not 0 <= start < end or end - start > 120:
        raise ValueError("Excerpt must be positive and no longer than 120 seconds.")
    chunks = []
    with av.open(str(path)) as container:
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
        # Decode sequentially to avoid codec preroll/seek timestamp ambiguity.
        offset = 0
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                samples = converted.to_ndarray().reshape(-1)
                left, right = max(0, int(start * 16000) - offset), min(len(samples), int(end * 16000) - offset)
                if right > left:
                    chunks.append(samples[left:right])
                offset += len(samples)
                if offset >= end * 16000:
                    return np.clip(np.concatenate(chunks), -1.0, 1.0)
    if not chunks:
        raise ValueError("Recording contains no audio in the requested interval.")
    return np.clip(np.concatenate(chunks), -1.0, 1.0)


def caption_reference(path: Path, start: float, end: float) -> str | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    # json3 automatic captions contain incremental word events; do not merge overlapping lines twice.
    words = []
    for event in data.get("events", []):
        base = event.get("tStartMs", 0) / 1000
        for segment in event.get("segs", []):
            timestamp = base + segment.get("tOffsetMs", 0) / 1000
            if start <= timestamp < end:
                words.append(segment.get("utf8", ""))
    return "".join(words).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--media", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", choices=["development", "held_out"], default="development")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    engine = SpeechEngine(args.media / "models")
    records = []
    for source in json.loads(args.sources.read_text(encoding="utf-8"))["sources"]:
        media = args.media / (source["id"] + ".webm")
        for start, end in source[args.split + "_windows"][:args.limit]:
            config = SpeechConfig(model=args.model, language=source["language"], device=args.device,
                                  compute_type="float16" if args.device == "cuda" else "int8")
            audio = excerpt(media, start, end)
            loaded = perf_counter()
            engine.prepare(config)
            model_load_seconds = perf_counter() - loaded
            result = engine.transcribe(audio, config)
            reference = caption_reference(args.media / f"{source['id']}.{source['language']}.json3", start, end)
            record = {"source_id": source["id"], "start": start, "end": end, "split": args.split,
                      "audio_sha256": hashlib.sha256(audio.tobytes()).hexdigest(),
                      "device": args.device, "compute_type": config.compute_type,
                      "model_load_seconds": model_load_seconds, **result.to_dict(),
                      "reference_provenance": "youtube_captions_unverified" if reference else "missing",
                      "caption_agreement": score(reference, result.text, source["language"]) if reference else None}
            records.append(record)
            args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({k: record[k] for k in ("source_id", "start", "end", "latency_seconds", "reference_provenance", "caption_agreement")}), flush=True)


if __name__ == "__main__":
    main()
