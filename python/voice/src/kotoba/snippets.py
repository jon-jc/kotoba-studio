"""Local saved phrases, ported from OpenWhispr's src/utils/snippets.ts.

Copyright (c) 2024 OpenWhispr Team. MIT; see THIRD_PARTY_LICENSES/OpenWhispr.txt.
Source: c6a871db1b8ada646eb728d3592431ecc8c17723. Expansion is explicit,
single-pass, longest-first, and limited to Unicode punctuation/space boundaries.
"""

import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata


def _fold(value: str) -> str:
    return unicodedata.normalize("NFC", value).replace("İ", "i").lower()


def validate_snippets(value: object) -> list[dict[str, str]]:
    """Validate editable/imported data before replacing the saved phrase collection."""
    if not isinstance(value, list) or len(value) > 200:
        raise ValueError("Use a list of at most 200 phrases. / 定型文は200件までです。")
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {"trigger", "replacement"}:
            raise ValueError("Each phrase needs trigger and replacement. / 合図と展開文が必要です。")
        trigger, replacement = item["trigger"], item["replacement"]
        if not isinstance(trigger, str) or not isinstance(replacement, str):
            raise ValueError("Phrase values must be text. / 文字列を入力してください。")
        trigger = unicodedata.normalize("NFC", trigger.strip())
        if not 1 <= len(trigger) <= 100 or not 1 <= len(replacement.strip()) <= 10000:
            raise ValueError("Use a 1–100 character trigger and 1–10000 character expansion. / 合図は1〜100文字、展開文は1〜10000文字です。")
        if _fold(trigger) in seen:
            raise ValueError("Duplicate phrase trigger. / 合図が重複しています。")
        seen.add(_fold(trigger))
        result.append({"trigger": trigger, "replacement": replacement})
    return result


def load_snippets(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    if path.stat().st_size > 10_000_000:
        raise ValueError("Phrase file is too large. / 定型文ファイルが大きすぎます。")
    return validate_snippets(json.loads(path.read_text(encoding="utf-8")))


def save_snippets(path: Path, snippets: list[dict[str, str]]) -> None:
    """Atomically replace local data; failed validation leaves existing data untouched."""
    content = json.dumps(validate_snippets(snippets), ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def expand_snippets(text: str, snippets: list[dict[str, str]]) -> str:
    """Expand spoken phrases once; replacements never become new triggers."""
    if not text or not snippets:
        return text
    replacements = {}
    for item in snippets:
        folded = unicodedata.normalize("NFC", item["trigger"].strip()).replace("İ", "i")
        replacements[folded.lower()] = item["replacement"]
        replacements.setdefault(folded.replace("I", "ı").lower(), item["replacement"])
    patterns = [(re.compile(re.escape(key).replace("i", "[iİ]").replace("ı", "[ıI]"), re.IGNORECASE), value)
                for key, value in sorted(replacements.items(), key=lambda pair: len(pair[0]), reverse=True)]
    text = unicodedata.normalize("NFC", text)
    def boundary(char):
        return char.isspace() or unicodedata.category(char)[0] in "PS"
    output, index = [], 0
    while index < len(text):
        matched = False
        if index == 0 or boundary(text[index - 1]):
            for pattern, replacement in patterns:
                match = pattern.match(text, index)
                if match and (match.end() == len(text) or boundary(text[match.end()])):
                    output.append(replacement)
                    index = match.end()
                    matched = True
                    break
        if not matched:
            output.append(text[index])
            index += 1
    return "".join(output)
