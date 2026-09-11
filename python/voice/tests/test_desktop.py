import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace
from time import monotonic
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from kotoba.desktop import Window
from kotoba.speech import Transcript


@pytest.fixture
def window(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("kotoba.desktop.QStandardPaths.writableLocation", lambda _: str(tmp_path))
    result = Window()
    yield result
    deadline = monotonic() + 5
    while result.job is not None and monotonic() < deadline:
        app.processEvents()
        QTest.qWait(5)
    assert result.job is None
    result.close()


def test_transcription_is_reviewed_without_automatic_agent_call(window):
    window.transcribed(Transcript("田中さん、15時です。", "ja", 1, (), 2, 0.4, "test", ()))
    assert window.draft.toPlainText() == "田中さん、15時です。"
    assert window.harness.client is None
    assert window.metrics[2].text() == "0.20×"


def test_language_switch_preserves_draft(window):
    window.draft.setPlainText("Deploy は15時です")
    window.switch_locale()
    assert window.locale == "en"
    assert window.draft.toPlainText() == "Deploy は15時です"
    assert window.send_button.text() == "Send reviewed text  →"


def test_notification_adapter_and_completed_turn(window):
    class Harness:
        def run(self, text, workspace, model, key, notify, provider="deepseek-official", key_ref=""):
            notify(SimpleNamespace(payload={"event": {"type": "tool/call"}}, method="session.event"))
            return SimpleNamespace(session_id="test-session", final_response="確認しました", finish_reason="completed", events=[{}])
        def close(self):
            pass
    window.apply_routes([{"id":"deepseek-official", "name":"DeepSeek", "models":[{"id":"deepseek-v4-flash"}], "key_ref":"DEEPSEEK_API_KEY", "configured":True}])
    window.harness = Harness()
    window.draft.setPlainText("確認してください")
    window.send()
    deadline = monotonic() + 5
    while window.job is not None and monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(5)
    assert window.job is None
    assert "tool/call" in window.activity.toPlainText()
    assert "確認しました" in window.conversation.toPlainText()
    assert window.entries[-1]["prompt"] == "確認してください"


def test_punctuation_only_reference_does_not_crash(window):
    window.reference.setPlainText("。")
    window.draft.setPlainText("誤認識")
    window.compare()
    assert "—" in window.score_label.text()


def settle(window):
    deadline = monotonic() + 5
    while window.job is not None and monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(5)
    assert window.job is None


def test_background_refresh_does_not_leave_voice_status_working(window):
    window.work(lambda emit: None, lambda _: None)
    settle(window)
    assert window.status.text() == window.t("ready")


@pytest.mark.parametrize("fails", [False, True])
def test_model_setup_progress_crosses_worker_thread_and_recovers(window, monkeypatch, fails):
    from threading import Event
    from PySide6.QtWidgets import QMessageBox
    from kotoba.model_progress import ModelProgress
    release = Event()
    errors = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: errors.append(args[-1]))
    def prepare(config, allow_download, progress):
        progress(ModelProgress("downloading", 1048576, 2097152))
        assert release.wait(5)
        if fails:
            raise RuntimeError("fixture connection interrupted")
        progress(ModelProgress("loading"))
    monkeypatch.setattr(window.engine, "prepare", prepare)
    window.set_locale("en")
    window.prepare()
    try:
        deadline = monotonic() + 5
        while window.download_progress.value() != 500 and monotonic() < deadline:
            QApplication.processEvents()
            QTest.qWait(5)
        assert window.download_progress.value() == 500
        assert not window.download_progress.isHidden()
        assert "1.0 / 2.0 MiB" in window.download_progress.format()
        assert not window.prepare_button.isEnabled()
    finally:
        release.set()
        settle(window)
    assert window.prepare_button.isEnabled()
    if fails:
        assert window.download_progress.isHidden()
        assert errors == ["fixture connection interrupted"]
    else:
        assert window.download_progress.value() == 100
        assert "Model ready" in window.status.text()


def test_unknown_model_size_and_loading_do_not_claim_completion(window):
    from kotoba.model_progress import ModelProgress
    window.set_locale("ja")
    window.show_model_progress(ModelProgress("downloading", 1048576))
    assert window.download_progress.maximum() == 0
    assert "1.0 MiB" in window.status.text()
    window.show_model_progress(ModelProgress("loading"))
    assert window.download_progress.maximum() == 0
    assert window.status.text() == "モデルを読み込み中…"


def test_missing_model_prompts_before_recording_then_explicit_retry(window, monkeypatch):
    from kotoba.speech_models import ModelDownloadRequired
    calls = []
    def prepare(config, allow_download=False):
        calls.append(allow_download)
        if len(calls) == 1: raise ModelDownloadRequired("fixture-model")
    monkeypatch.setattr(window.engine, "prepare", prepare)
    monkeypatch.setattr(window, "offer_model_download", lambda config, model: calls.append(model))
    monkeypatch.setattr(window, "start_recording", lambda: calls.append("capture"))
    window.record()
    settle(window)
    assert calls == [False, "fixture-model"]
    assert window.stream is None
    window.record()
    settle(window)
    assert calls[-2:] == [False, "capture"]


def test_route_selection_clears_stale_model_and_session_key(window):
    routes = [
        {"id":"deepseek-official", "name":"DeepSeek", "configured":True, "key_ref":"DEEPSEEK_API_KEY", "models":[{"id":"deepseek-v4-flash"}]},
        {"id":"kotoba-local", "name":"Local", "configured":True, "key_ref":"LOCAL_KEY", "models":[{"id":"qwen-local"}]},
        {"id":"anthropic", "name":"Anthropic", "configured":False, "key_ref":"", "models":[]},
    ]
    window.apply_routes(routes)
    window.api_key = "fixture-deepseek-key"
    window.agent_provider.setCurrentIndex(window.agent_provider.findData("kotoba-local"))
    assert window.model == "qwen-local" and window.api_key == ""
    window.agent_model.setCurrentText("custom-local")
    window.switch_locale()
    assert window.model == "custom-local"
    window.agent_provider.setCurrentIndex(window.agent_provider.findData("anthropic"))
    assert window.model == "" and not window.agent_model.isEnabled()


def test_language_preference_survives_interface_switch(window):
    window.language.setCurrentIndex(window.language.findData("en"))
    window.switch_locale()
    assert window.language.currentData() == "en"
    assert window.preferences.value("speech/language") == "en"


@pytest.mark.parametrize("download", [False, True])
def test_setup_prompt_requires_download_choice_and_never_starts_capture(window, monkeypatch, download):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QMessageBox
    from kotoba.speech import SpeechConfig
    calls = []
    window.set_locale("en")
    window.global_dictation.target = (100, 20)
    monkeypatch.setattr(window.engine, "prepare", lambda config, allow_download, progress: calls.append((config.language, allow_download)))
    def choose():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QMessageBox)
        assert "audio is not uploaded" in dialog.informativeText()
        if download:
            next(b for b in dialog.buttons() if dialog.buttonRole(b) == QMessageBox.AcceptRole).click()
        else:
            dialog.button(QMessageBox.Cancel).click()
    QTimer.singleShot(0, choose)
    window.offer_model_download(SpeechConfig(language="en"), "fixture-model")
    settle(window)
    assert calls == ([("en", True)] if download else [])
    assert window.stream is None and window.global_dictation.target is None


def test_settings_uses_provider_models_and_applies_selected_route(window):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QComboBox, QDialog
    window.apply_routes([
        {"id":"deepseek-official", "name":"DeepSeek", "configured":True, "key_ref":"DEEPSEEK_API_KEY", "models":[{"id":"deepseek-v4-flash"}]},
        {"id":"openai", "name":"OpenAI", "configured":True, "key_ref":"OPENAI_API_KEY", "models":[{"id":"openai-fixture"}]},
    ])
    def choose():
        dialog = QApplication.activeModalWidget()
        combos = dialog.findChildren(QComboBox)
        provider = next(c for c in combos if c.findData("openai") >= 0)
        provider.setCurrentIndex(provider.findData("openai"))
        model = next(c for c in combos if c.isEditable())
        assert model.currentText() == "openai-fixture"
        model.setCurrentText("custom-openai-model")
        dialog.accept()
    QTimer.singleShot(0, choose)
    window.settings_dialog()
    assert window.provider == "openai" and window.model == "custom-openai-model"
    assert window.agent_model.currentText() == "custom-openai-model"


def test_route_refresh_does_not_interrupt_recording(window, monkeypatch):
    window.runtime_url = "http://127.0.0.1:1"
    marker = object()
    window.stream = marker
    monkeypatch.setattr(window, "work", lambda *args: pytest.fail("Recording must keep Stop available"))
    try:
        window.refresh_routes()
        assert window.record_button.isEnabled()
    finally:
        window.stream = None


def test_removed_provider_clears_model_without_changing_saved_choice(window):
    provider = window.provider
    window.apply_routes([])
    assert window.agent_provider.currentIndex() == -1
    assert window.agent_model.currentText() == ""
    assert not window.agent_model.isEnabled()
    assert window.route_label.text() == ""
    assert window.provider == provider
    window.apply_routes([{"id":"new", "name":"New", "models":[{"id":"model"}], "configured":True}])
    window.agent_provider.setCurrentIndex(0)
    assert window.provider == "new" and window.model == "model"


def test_missing_audio_source_has_actionable_message(window, monkeypatch):
    errors = []
    monkeypatch.setattr(window, "failure", errors.append)
    window.audio_source.clear()
    window.start_recording()
    assert window.stream is None
    assert errors and "NoneType" not in errors[0]


def test_empty_recording_never_starts_inference(window, monkeypatch):
    errors = []
    monkeypatch.setattr(window, "failure", errors.append)
    monkeypatch.setattr(window, "transcribe", lambda *_: pytest.fail("Empty audio must not reach inference"))
    window.stream = SimpleNamespace(stop=lambda:None, close=lambda:None)
    window.frames = []
    window.record_error = ""
    window.record()
    assert window.stream is None and window.record_button.isEnabled()
    assert errors
