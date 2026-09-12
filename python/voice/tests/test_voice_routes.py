import httpx
import numpy as np
import pytest
from kotoba.speech import SpeechConfig, SpeechEngine
from kotoba.speech_models import resolve_model, JAPANESE_MODEL, prepare_parakeet
from kotoba.cloud_speech import CloudSpeech


def test_language_defaults_and_incompatible_models():
    assert resolve_model("auto", "en") == "parakeet-unified-en-0.6b"
    assert resolve_model("auto", "ja") == JAPANESE_MODEL
    assert resolve_model("auto", "auto") == "turbo"
    for model, language in (("parakeet-unified-en-0.6b", "ja"), (JAPANESE_MODEL, "en")):
        with pytest.raises(ValueError): resolve_model(model, language)


def test_offline_parakeet_never_downloads_missing_weights(tmp_path, monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: pytest.fail("Unexpected network request"))
    with pytest.raises(RuntimeError, match="Download"):
        prepare_parakeet(tmp_path, "parakeet-unified-en-0.6b", False)


def test_offline_whisper_sets_local_only_and_meeting_vad(tmp_path):
    seen = {}
    class Model:
        def transcribe(self, audio, **kwargs):
            seen.update(kwargs)
            from types import SimpleNamespace
            return [], SimpleNamespace(language="ja", language_probability=1)
    def factory(*args, **kwargs):
        assert kwargs['local_files_only'] is True
        return Model()
    SpeechEngine(tmp_path, factory).transcribe(np.full(16000, .1), SpeechConfig(context="meeting"))
    assert seen['vad_filter'] is True
    assert seen['chunk_length'] == 15
    assert seen['word_timestamps'] is False


def test_cloud_is_explicit_wav_upload_and_keeps_japanese(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.headers['authorization'] == "Bearer fixture-key"
        assert b"RIFF" in request.content
        assert b'\r\nja\r\n' in request.content
        return httpx.Response(200, json={"text": "次回は金曜日です。"})
    engine = SpeechEngine(tmp_path, lambda *a, **k: pytest.fail("Unexpected local model"))
    engine.cloud = CloudSpeech("https://speech.example/v1/audio/transcriptions", "fixture", "fixture-key", httpx.MockTransport(handler))
    result = engine.transcribe(np.full(16000, .1), SpeechConfig(processing="cloud"))
    assert result.text == "次回は金曜日です。" and len(calls) == 1
    assert result.model == "cloud:fixture"


@pytest.mark.parametrize("status", [302, 401, 429, 500])
def test_cloud_never_redirects_retries_or_falls_back(tmp_path, status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"location": "https://other.example"}, text="fixture-key should not be reported")
    engine = SpeechEngine(tmp_path, lambda *a, **k: pytest.fail("Unexpected fallback"))
    engine.cloud = CloudSpeech("https://speech.example/transcribe", "fixture", "fixture-key", httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as error:
        engine.transcribe(np.full(16000, .1), SpeechConfig(processing="cloud"))
    assert "fixture-key" not in str(error.value)
    assert len(calls) == 1


def test_missing_whisper_cache_has_actionable_setup_error(tmp_path, monkeypatch):
    from huggingface_hub.errors import LocalEntryNotFoundError
    from kotoba.speech_models import ModelDownloadRequired
    def absent(*args, **kwargs):
        assert kwargs["local_files_only"] is True
        raise LocalEntryNotFoundError("fixture missing snapshot")
    monkeypatch.setattr("faster_whisper.utils.download_model", absent)
    with pytest.raises(ModelDownloadRequired) as error:
        SpeechEngine(tmp_path).prepare(SpeechConfig(model="turbo", language="en"), allow_download=False)
    assert error.value.model == "turbo"


def test_catalog_joins_configured_custom_and_unconfigured_routes(monkeypatch):
    from kotoba.voice_routes import load_routes
    responses = {
        "llm/listProviders": [{"id":"deepseek-official", "name":"DeepSeek"}, {"id":"custom", "name":"Private Gateway"}],
        "session/modelCatalog": {"groups":[{"id":"deepseek-official", "configured":False, "models":[{"id":"deepseek-model"}]}, {"id":"custom", "models":[{"id":"voice-agent"}]}]},
        "llm/listConfigurableProviders": [
            {"provider":"custom", "settingsNs":"llm-pi-ai", "settingsPath":["providers", "custom"]},
            {"provider":"openai", "displayName":"OpenAI"}],
        "settings/describe": {"namespaces":[{"ns":"llm-pi-ai", "value":{"providers":{"custom":{"apiKeyEnv":"CUSTOM_KEY"}}}}]},
    }
    class Remote:
        def __init__(self, url): pass
        def call(self, method, args): return responses[method]
    monkeypatch.setattr("kotoba.voice_routes.HarnessRemote", Remote)
    routes = load_routes("fixture")
    assert routes[2]["id"] == "openai" and routes[2]["configured"] is False
    assert routes[1]["id"] == "deepseek-official" and routes[1]["configured"] is False
    assert routes[0]["models"] == [{"id":"voice-agent"}]
    assert routes[0]["key_ref"] == "CUSTOM_KEY"


@pytest.mark.parametrize("provider,ref", [("openai","OPENAI_API_KEY"), ("anthropic","ANTHROPIC_API_KEY"), ("moonshotai","MOONSHOT_API_KEY"), ("custom","GATEWAY_KEY")])
def test_voice_session_routes_keys_to_selected_provider(tmp_path, monkeypatch, provider, ref):
    from types import SimpleNamespace
    from kotoba.harness import HarnessSession
    configs = []
    class Client:
        def __init__(self, **kwargs): configs.append(kwargs)
        def run(self, *args, **kwargs): return SimpleNamespace(finish_reason="completed")
        def close(self): pass
    monkeypatch.setattr("deepseek_harness.DeepSeekHarness", Client)
    monkeypatch.setattr("kotoba.harness.runtime_path", lambda: tmp_path / "runtime")
    session = HarnessSession(tmp_path)
    try:
        session.run("hello", str(tmp_path), "selected-model", "fixture-key", lambda _:None, provider=provider, key_ref=ref)
        assert configs[0]["provider"] == provider
        assert configs[0]["env"][ref] == "fixture-key"
        assert "DEEPSEEK_API_KEY" not in configs[0]["env"]
        assert configs[0]["api_key"] is None
    finally:
        session.close()
