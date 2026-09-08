from types import SimpleNamespace
import numpy as np
import pytest
from kotoba.speech import SpeechConfig, SpeechEngine
from kotoba.evaluate import evaluate, score


def test_silence_never_loads_model_or_hallucinates(tmp_path):
    engine = SpeechEngine(tmp_path, lambda *a, **kw: pytest.fail("Silence loaded model"))
    result = engine.transcribe(np.zeros(16000), SpeechConfig())
    assert result.text == ""
    assert result.review_reasons == ("no_speech",)


@pytest.mark.parametrize("language", ["ja", "en", "auto"])
def test_transcription_preserves_original_language_and_flags_uncertainty(tmp_path, language):
    class Model:
        def transcribe(self, audio, **options):
            assert options["task"] == "transcribe"
            assert options["language"] == (None if language == "auto" else language)
            assert options["vad_filter"] is True
            assert options["condition_on_previous_text"] is False
            assert options["hotwords"] == "田中 Kubernetes"
            return iter([SimpleNamespace(start=0, end=1, text=" 田中さん、deployします。", avg_logprob=-1.2, no_speech_prob=0.1)]), SimpleNamespace(language="ja", language_probability=0.7)
    engine = SpeechEngine(tmp_path, lambda *a, **kw: Model())
    result = engine.transcribe(np.full(16000, 0.1), SpeechConfig(language=language, glossary="田中 Kubernetes"))
    assert result.text == "田中さん、deployします。"
    assert "low_decoder_score" in result.review_reasons
    assert ("language_uncertain" in result.review_reasons) == (language == "auto")


@pytest.mark.parametrize("audio", [np.array([]), np.array([float("nan")]), np.zeros((2, 10)), np.array([2.0]), np.zeros(16001)])
def test_invalid_or_oversized_audio_rejected_before_inference(tmp_path, audio):
    engine = SpeechEngine(tmp_path, lambda *a, **kw: pytest.fail("Invalid audio reached inference"))
    with pytest.raises(ValueError):
        engine.transcribe(audio, SpeechConfig(max_seconds=1))


def test_japanese_cer_measures_number_errors_without_space_tokenization():
    result = score("会議は１５時です。", "会議は14時です", "ja")
    assert result["metric"] == "CER"
    assert result["errors"] == 1
    assert result["reference_units"] == 8


def test_english_wer_and_silence_have_distinct_denominators():
    report = evaluate([{"language": "en", "reference": "Deploy at five", "hypothesis": "deploy at nine"},
                       {"language": "ja", "reference": "", "hypothesis": "ありがとうございました"}])
    assert report["summary"]["en"]["error_rate"] == pytest.approx(1 / 3)
    assert report["summary"]["ja"]["error_rate"] is None
    assert report["silence_hallucinations"] == 1
