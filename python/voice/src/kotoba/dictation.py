"""OpenWhispr-derived dictionary echo detection, adapted to preserve ASR evidence.

Copyright (c) 2024 OpenWhispr Team. MIT; see THIRD_PARTY_LICENSES/OpenWhispr.txt.
Port of src/utils/dictionaryEchoFilter.js at c6a871db1b8ada646eb728d3592431ecc8c17723.
Unlike upstream rejection, this integration only flags suspected echo for review.
"""

from collections import Counter
import re
import unicodedata


def _normalize(text):
    return " ".join("".join(c for c in text.lower() if c.isspace() or unicodedata.category(c)[0] in "LN").split())


def dictionary_echo(text: str, glossary: str) -> bool:
    normalized, prompt = _normalize(text), _normalize(glossary)
    if not normalized or not prompt:
        return False
    words = normalized.split()
    unique = set(words)
    overlap = len(unique & set(prompt.split())) / len(unique)
    if overlap < 0.9:
        return False
    counts = Counter(words)
    if max(counts.values()) >= 3:
        return True
    if re.search(r"[,、，]\s*$", text) and len(normalized) <= 30:
        return True
    sequence = [(word, index) for index, term in enumerate(re.split(r"[,、，]", glossary))
                for word in _normalize(term).split()]
    if re.search(r"[,、，]", text):
        for start in range(len(sequence) - len(words) + 1):
            run = sequence[start:start + len(words)]
            if [w for w, i in run] == words and run[-1][1] - run[0][1] + 1 >= 3:
                return True
    return False


def format_dictation(text: str) -> str:
    """Conservative spacing cleanup; no translation, filler deletion, or number rewriting."""
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.strip().splitlines())
