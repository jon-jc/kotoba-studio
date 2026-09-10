"""Exercise native controls without launching a runtime or downloading speech models."""

import pytest


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("KOTOBA_HOME", str(tmp_path))
    from PySide6.QtWidgets import QApplication
    from kotoba import desktop
    from kotoba.workspace import Workspace
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(desktop, "sources", lambda: [])
    monkeypatch.setattr(Workspace, "start_backend", lambda self: None)
    window = Workspace()
    yield window
    window.close()
    from PySide6.QtCore import QCoreApplication, QEvent
    window.web.page().deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def test_top_right_locale_preserves_work_and_persists(workspace):
    window = workspace
    window.voice.draft.setPlainText("確認する deploy at 15:00")
    window.voice.reference.setPlainText("正解文")
    window.voice.speak.setChecked(True)
    window.command.setText("$value = '日本語'")
    window.console.setPlainText("existing output")
    window.stack.setCurrentIndex(3)
    page = window.web.page()
    window.locale_toggle.setCurrentIndex(window.locale_toggle.findData("en"))
    assert window.nav[3].accessibleName() == "›_  Terminal"
    assert window.voice.draft.toPlainText() == "確認する deploy at 15:00"
    assert window.voice.reference.toPlainText() == "正解文"
    assert window.voice.speak.isChecked()
    assert window.voice.preferences.value("locale") == "en"
    window.locale_toggle.setCurrentIndex(window.locale_toggle.findData("ja"))
    assert window.nav[3].accessibleName() == "›_  ターミナル"
    assert "コマンドを検索" in window.command_center.text()
    assert "表示言語" in window.locale_scope.text()
    assert window.command.text() == "$value = '日本語'"
    assert window.console.toPlainText() == "existing output"
    assert window.stack.currentIndex() == 3 and window.web.page() is page
    window.voice.busy(True)
    assert not window.locale_toggle.isEnabled()
    window.voice.busy(False)
    assert window.locale_toggle.isEnabled()


def test_phrase_expansion_undo_and_reviewed_handoff(workspace):
    from PySide6.QtWidgets import QApplication
    voice = workspace.voice
    voice.snippets = [{"trigger": "議事録", "replacement": "議題\n決定事項\n担当者"}]
    voice.draft.setPlainText("議事録。")
    voice.expand_phrases()
    assert voice.draft.toPlainText() == "議題\n決定事項\n担当者。"
    voice.draft.undo()
    assert voice.draft.toPlainText() == "議事録。"
    workspace.stack.setCurrentIndex(1)
    voice.handoff()
    assert QApplication.clipboard().text() == "議事録。"
    assert voice.draft.toPlainText() == "議事録。"
    assert workspace.stack.currentIndex() == 0
    assert voice.job is None


def test_docks_preserve_work_and_do_not_replace_editor(workspace):
    workspace.voice.draft.setPlainText("設計を確認")
    workspace.console.setPlainText("terminal history")
    workspace.show_panel(2)
    workspace.show_panel(1)
    assert workspace.voice.isHidden()
    workspace.show_panel(3)
    assert not workspace.terminal_dock.isHidden()
    assert workspace.stack.currentIndex() == 2
    workspace.show_panel(1)
    workspace.show_panel(3)
    assert workspace.voice.draft.toPlainText() == "設計を確認"
    assert workspace.console.toPlainText() == "terminal history"
    assert workspace.stack.currentIndex() == 2


def test_command_palette_search_dispatches_action(workspace):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLineEdit
    workspace.voice.set_locale("en")
    errors = []
    def choose():
        dialog = QApplication.activeModalWidget()
        try:
            query = dialog.findChild(QLineEdit)
            query.setText("Local models")
            query.returnPressed.emit()
        except Exception as error:
            errors.append(error)
        finally:
            dialog.reject()
    QTimer.singleShot(0, choose)
    workspace.command_palette()
    assert not errors
    assert workspace.stack.currentWidget() is workspace.local_models


def test_phrase_editor_saves_local_data_and_cancel_preserves_it(workspace):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QPushButton
    from kotoba.snippets import load_snippets
    voice = workspace.voice
    voice.set_locale("en")
    errors = []
    def edit():
        dialog = QApplication.activeModalWidget()
        try:
            dialog.findChild(QLineEdit).setText("meeting template")
            dialog.findChild(QPlainTextEdit).setPlainText("議題\nActions")
            buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
            buttons["Apply phrase"].click()
            buttons["Save"].click()
        except Exception as error:
            errors.append(error)
        finally:
            dialog.reject()
    QTimer.singleShot(0, edit)
    voice.edit_snippets()
    assert not errors
    expected = [{"trigger": "meeting template", "replacement": "議題\nActions"}]
    assert voice.snippets == expected
    assert load_snippets(voice.home / "snippets.json") == expected
    def cancel():
        dialog = QApplication.activeModalWidget()
        dialog.findChild(QLineEdit).setText("discard this")
        dialog.reject()
    QTimer.singleShot(0, cancel)
    voice.edit_snippets()
    assert load_snippets(voice.home / "snippets.json") == expected
