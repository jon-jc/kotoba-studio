from pathlib import Path
import json
import sqlite3
import pytest
from kotoba.collaboration import (CollaborationStore, new_document, source_token,
    translation_prompt, parse_translation, markdown)


def response(document):
    return json.dumps({"source_token": source_token(document), "english": "Release timing is undecided.",
        "japanese": "リリース日は未定です。", "items": [{"kind": "question", "english": "When is release?",
        "japanese": "リリース日はいつですか？", "owner": "", "due": "", "quote": "リリース日は未定"}]}, ensure_ascii=False)


def test_roundtrip_revision_conflict_preserves_winner(tmp_path):
    store = CollaborationStore(tmp_path / "team.db")
    identity = store.create("引き継ぎ", "リリース日は未定")
    revision, doc = store.read(identity)
    doc["english"] = "Undecided"
    assert store.save(identity, revision, doc) == 2
    doc["english"] = "stale"
    with pytest.raises(ValueError, match="another window"):
        store.save(identity, revision, doc)
    assert CollaborationStore(store.path).read(identity)[1]["english"] == "Undecided"
    assert store.search("リリース") == [(identity, "引き継ぎ")]
    assert store.search("%") == []
    with pytest.raises(ValueError):
        store.delete(identity, revision)
    store.delete(identity, 2)
    assert store.search() == []


def test_future_schema_refused_without_changing_data(tmp_path):
    path = tmp_path / "team.db"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=2")
    with pytest.raises(ValueError, match="newer"):
        CollaborationStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2


def test_import_requires_current_source_and_glossary_and_resets_review():
    doc = new_document("Handoff", "リリース日は未定")
    result = response(doc)
    doc["reviewed"] = True
    imported = parse_translation(result, doc)
    assert imported["source"] == doc["source"]
    assert not imported["reviewed"] and not imported["items"][0]["reviewed"]
    assert imported["items"][0]["owner"] == ""
    doc["glossary"] = "release = リリース"
    with pytest.raises(ValueError, match="Source or glossary"):
        parse_translation(result, doc)
    doc["glossary"] = ""
    doc["source"] += "明日に決定"
    with pytest.raises(ValueError):
        parse_translation(result, doc)


@pytest.mark.parametrize("mutation", [
    lambda r: r["items"][0].update(quote="田中さんが担当"),
    lambda r: r["items"][0].update(quote=""),
    lambda r: r["items"][0].update(kind="execute"),
    lambda r: r["items"][0].update(owner={"name": "Tanaka"}),
    lambda r: r.update(english=None),
    lambda r: r.update(items=[None]),
    lambda r: r.update(items=r["items"] * 201),
])
def test_rejects_unsupported_quotes_and_malformed_model_output(mutation):
    doc = new_document(source="リリース日は未定")
    raw = json.loads(response(doc))
    mutation(raw)
    with pytest.raises(ValueError):
        parse_translation(json.dumps(raw), doc)
    assert doc["items"] == []


def test_prompt_and_export_keep_uncertainty_original_and_review_labels():
    doc = new_document("Release / リリース", "リリース日は未定")
    assert source_token(doc) in translation_prompt(doc)
    assert "Do not use tools" in translation_prompt(doc)
    result = parse_translation("```json\n" + response(doc) + "\n```", doc)
    exported = markdown(result)
    assert "Needs review / 要確認" in exported
    assert "Unassigned / 未定" in exported
    assert "Unspecified / 未定" in exported
    assert "## Original context / 原文\n\nリリース日は未定" in exported
    assert "Release timing is undecided." in exported
    assert "リリース日は未定です。" in exported
    assert exported == (Path(__file__).parent / "expected" / "bilingual-handoff.md").read_text(encoding="utf-8")
