"""Complete the pinned agent workspace's Japanese catalog before packaging."""
import json
import re
from pathlib import Path


def flatten_strings(value, prefix=""):
    result = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            result.update(flatten_strings(child, path))
        elif isinstance(child, str):
            result[path] = child
    return result


def complete_catalog(english, japanese, supplement):
    source = flatten_strings(english)
    unknown = supplement.keys() - source.keys()
    if unknown:
        raise ValueError(f"Japanese supplement contains unknown keys: {sorted(unknown)[:5]}")
    for key, value in supplement.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Empty Japanese translation: {key}")
        if sorted(re.findall(r"{{.*?}}", value)) != sorted(re.findall(r"{{.*?}}", source[key])):
            raise ValueError(f"Japanese interpolation mismatch: {key}")

    # Walk the original structure: keys themselves can contain dots.
    def merge(en, ja, prefix=""):
        out = dict(ja)
        for key, child in en.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(child, dict):
                out[key] = merge(child, ja.get(key, {}), path)
            elif path in supplement:
                out[key] = supplement[path]
        return out

    result = merge(english, japanese)
    missing = source.keys() - flatten_strings(result).keys()
    if missing:
        raise ValueError(f"Missing Japanese translations: {sorted(missing)[:5]}")
    return result


def prepare_locale(root):
    locales = root / "src/renderer/src/i18n/locales"
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    result = complete_catalog(read(locales / "en.json"), read(locales / "ja.json"),
                              read(Path(__file__).with_name("fleet_ja_supplement.json")))
    (locales / "ja.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8", newline="\n")
