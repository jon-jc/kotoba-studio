import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("prepare_fleet_locale", Path(__file__).parents[1] / "prepare_fleet_locale.py")
locale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locale)


def test_catalog_preserves_existing_translations_and_dotted_keys():
    en = {"chat": {"title": "Chat", "error.auth": "Sign in as {{name}}"}}
    ja = {"chat": {"title": "チャット"}}
    supplement = {"chat.error.auth": "{{name}} としてサインイン"}
    result = locale.complete_catalog(en, ja, supplement)
    assert result == {"chat": {"title": "チャット", "error.auth": "{{name}} としてサインイン"}}
    assert locale.complete_catalog(en, result, supplement) == result
    assert ja == {"chat": {"title": "チャット"}}


@pytest.mark.parametrize("supplement, reason", [
    ({}, "Missing Japanese"),
    ({"error": "サインイン"}, "interpolation mismatch"),
    ({"error": ""}, "Empty Japanese"),
    ({"unknown": "不明"}, "unknown keys"),
])
def test_catalog_rejects_gaps_and_broken_interpolation(supplement, reason):
    with pytest.raises(ValueError, match=reason):
        locale.complete_catalog({"error": "Sign in as {{name}}"}, {}, supplement)
