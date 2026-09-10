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
    original_clipboard = app.clipboard().text()
    yield window
    app.clipboard().setText(original_clipboard)
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


def test_source_tabs_search_preserve_files_and_reject_binary(workspace, tmp_path):
    first = tmp_path / "日本語.py"
    first.write_text("name = 'ことば'\nprint(name)\n", encoding="utf-8")
    second = tmp_path / "readme.md"
    second.write_text("Kotoba Studio", encoding="utf-8")
    tabs = workspace.source_tabs
    workspace.view_file(workspace.files.index(str(first)))
    editor = tabs.tabs.currentWidget()
    assert editor.isReadOnly()
    assert editor.blockCount() == 3
    assert editor.font().family() == "Consolas"
    assert editor.highlighter.lines
    tabs.query.setText("name")
    assert editor.textCursor().selectedText() == "name"
    tabs.find_text()
    assert editor.textCursor().blockNumber() == 1
    tabs.find_text()
    assert editor.textCursor().blockNumber() == 0
    tabs.find_text(backward=True)
    assert editor.textCursor().blockNumber() == 1
    workspace.view_file(workspace.files.index(str(second)))
    assert tabs.tabs.count() == 2
    workspace.view_file(workspace.files.index(str(first)))
    assert tabs.tabs.count() == 2 and tabs.tabs.currentWidget() is editor
    workspace.voice.set_locale("ja")
    assert "読み取り専用" in tabs.position.text()
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\x00binary")
    workspace.view_file(workspace.files.index(str(binary)))
    assert tabs.tabs.currentWidget() is editor
    assert editor.toPlainText() == first.read_text(encoding="utf-8")
    tabs.close_tab(tabs.tabs.currentIndex())
    assert tabs.tabs.count() == 1


def test_reviewed_handoff_pastes_without_submitting(workspace):
    from time import monotonic
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QUrl
    from PySide6.QtWebEngineCore import QWebEnginePage
    original = workspace.web.page()
    page = QWebEnginePage(workspace.browser_profile, workspace.web)
    workspace.web.setPage(page)
    original.deleteLater()
    workspace.show()
    loaded = []
    page.loadFinished.connect(loaded.append)
    page.setHtml('<div data-composer-input contenteditable="true">Existing draft</div><button onclick="document.body.dataset.sent=1">Send</button>', QUrl("about:blank"))
    def until(predicate):
        deadline = monotonic() + 10
        while not predicate() and monotonic() < deadline:
            QTest.qWait(10)
        assert predicate()
    until(lambda: bool(loaded))
    workspace.handoff_draft("日本語 and English")
    observed = []
    def read():
        observed.clear()
        page.runJavaScript("document.querySelector('[data-composer-input]').innerText", observed.append)
        until(lambda: bool(observed))
        return observed[0]
    deadline = monotonic() + 10
    while "日本語" not in read() and monotonic() < deadline:
        QTest.qWait(10)
    # Chromium's plain contenteditable inserts paragraph blocks; Lexical owns its own paste formatting.
    assert [line for line in read().splitlines() if line] == ["Existing draft", "日本語 and English"]
    sent = []
    page.runJavaScript("document.body.dataset.sent || 'no'", sent.append)
    until(lambda: bool(sent))
    assert sent == ["no"]
    workspace.voice.set_locale("ja")
    assert "チャットに追加しました" in workspace.health.text()
    page.setHtml('<p>No composer</p>', QUrl("about:blank"))
    loaded.clear()
    until(lambda: bool(loaded))
    workspace.handoff_draft("Copied fallback")
    until(lambda: workspace.health_key == "paste")
    assert QApplication.clipboard().text() == "Copied fallback"
