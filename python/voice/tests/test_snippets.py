import pytest

from kotoba.snippets import expand_snippets, load_snippets, save_snippets, validate_snippets


def test_longest_phrase_wins_and_expansion_is_not_recursive():
    phrases = [{"trigger": "meeting", "replacement": "会議"},
               {"trigger": "meeting template", "replacement": "meeting\nAgenda:\nActions:"}]
    assert expand_snippets("MEETING TEMPLATE. meeting!", phrases) == "meeting\nAgenda:\nActions:. 会議!"


def test_japanese_requires_phrase_boundaries_and_preserves_numbers():
    phrases = [{"trigger": "署名", "replacement": "田中 太郎\n開発部"}]
    assert expand_snippets("電子署名。署名、15時。", phrases) == "電子署名。田中 太郎\n開発部、15時。"
    assert expand_snippets("署名する", phrases) == "署名する"


def test_regex_characters_are_literal_and_unicode_is_normalized():
    phrases = [{"trigger": "a+b", "replacement": "$1\\test"}, {"trigger": "が", "replacement": "GA"}]
    assert expand_snippets("a+b, aaab, か\u3099", phrases) == "$1\\test, aaab, GA"


def test_saved_phrases_round_trip_and_invalid_update_preserves_file(tmp_path):
    path = tmp_path / "snippets.json"
    assert load_snippets(path) == []
    phrases = [{"trigger": "議事録", "replacement": "議題\n決定事項\n担当者"}]
    save_snippets(path, phrases)
    assert load_snippets(path) == phrases
    with pytest.raises(ValueError):
        save_snippets(path, [{"trigger": "", "replacement": "no"}])
    assert load_snippets(path) == phrases
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("value", [{}, [1], [{"trigger": 1, "replacement": "x"}],
    [{"trigger": "a", "replacement": "x"}, {"trigger": "A", "replacement": "y"}]])
def test_invalid_import_is_rejected(value):
    with pytest.raises(ValueError):
        validate_snippets(value)
