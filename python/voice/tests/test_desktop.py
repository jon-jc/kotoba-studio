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
        def run(self, text, workspace, model, key, notify):
            notify(SimpleNamespace(payload={"event": {"type": "tool/call"}}, method="session.event"))
            return SimpleNamespace(session_id="test-session", final_response="確認しました", finish_reason="completed", events=[{}])
        def close(self):
            pass
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
