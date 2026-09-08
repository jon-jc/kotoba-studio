"""Reference-based bilingual evaluation; no fabricated benchmark results."""

import argparse
import json
from pathlib import Path
import unicodedata


def normalize(text: str) -> str:
    """NFKC, casefold, punctuation removal; preserve kana, kanji, and numbers."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join("".join(c for c in text if not unicodedata.category(c).startswith("P")).split())


def distance(reference, hypothesis) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(hypothesis, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def score(reference: str, hypothesis: str, language: str) -> dict:
    if language not in {"ja", "en", "mixed"}:
        raise ValueError("Evaluation language must be ja, en, or mixed.")
    ref, hyp = normalize(reference), normalize(hypothesis)
    tokens = (lambda s: s.split()) if language == "en" else (lambda s: list(s.replace(" ", "")))
    r, h = tokens(ref), tokens(hyp)
    errors = distance(r, h)
    return {"metric": "WER" if language == "en" else "CER", "errors": errors,
            "reference_units": len(r), "error_rate": errors / len(r) if r else None,
            "silence_hallucination": not r and bool(h), "exact_match": ref == hyp}


def evaluate(rows: list[dict]) -> dict:
    results = [{**row, **score(row["reference"], row["hypothesis"], row["language"])} for row in rows]
    summary = {}
    for language in ("ja", "en", "mixed"):
        subset = [r for r in results if r["language"] == language and r["reference_units"]]
        units = sum(r["reference_units"] for r in subset)
        summary[language] = {"samples": len(subset), "error_rate": sum(r["errors"] for r in subset) / units if units else None}
    return {"normalization": "NFKC + casefold + punctuation removal; Japanese/mixed CER, English WER",
            "summary": summary, "silence_hallucinations": sum(r["silence_hallucination"] for r in results), "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSONL with reference, hypothesis, language")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    args.output.write_text(json.dumps(evaluate(rows), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
