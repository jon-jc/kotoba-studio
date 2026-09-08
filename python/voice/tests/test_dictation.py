from kotoba.dictation import dictionary_echo, format_dictation


def test_ordinary_dictionary_words_are_not_discarded():
    assert not dictionary_echo("Electron renderer", "Electron, renderer, Kubernetes")
    assert not dictionary_echo("yes yes", "yes, no")


def test_looped_dictionary_output_is_flagged():
    assert dictionary_echo("Kubernetes Kubernetes Kubernetes", "Kubernetes, deploy")
    assert dictionary_echo("testing, ", "testing, deploy")


def test_cleanup_preserves_japanese_english_and_numbers():
    assert format_dictation("  田中さん  deploy １５時。\n  えー、確認します。 ") == "田中さん deploy １５時。\nえー、確認します。"
