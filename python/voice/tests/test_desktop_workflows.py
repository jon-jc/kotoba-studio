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
    original_quit_policy = app.quitOnLastWindowClosed()
    monkeypatch.setattr(app, "quit", lambda: None)
    yield window
    app.clipboard().setText(original_clipboard)
    window.exit_requested = True
    window.close()
    app.setQuitOnLastWindowClosed(original_quit_policy)
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


def test_voice_tabs_and_routes_require_deliberate_selection(workspace):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    voice = workspace.voice
    workspace.show()
    workspace.show_panel(1)
    QApplication.processEvents()
    bar = voice.tabs.tabBar()
    voice.tabs.setCurrentIndex(1)
    # Isolate selection behavior from live provider discovery and agent requests.
    voice.agent_provider.blockSignals(True)
    voice.agent_model.blockSignals(True)
    for combo in (voice.agent_provider, voice.agent_model):
        combo.setEnabled(True)
        combo.clear()
        combo.addItems(["First", "Second", "Third"])
        combo.setCurrentIndex(1)

    for control in (bar, voice.agent_provider, voice.agent_model):
        for focused in (False, True):
            control.setFocus() if focused else control.clearFocus()
            for delta in (-120, 120):
                event = QWheelEvent(QPointF(10, 10), QPointF(control.mapToGlobal(QPoint(10, 10))),
                    QPoint(), QPoint(0, delta), Qt.NoButton, Qt.NoModifier,
                    Qt.ScrollUpdate, False)
                QApplication.sendEvent(control, event)
                assert control.currentIndex() == 1

    QTest.mouseClick(bar, Qt.LeftButton, pos=bar.tabRect(0).center())
    assert voice.tabs.currentIndex() == 0
    QTest.keyClick(bar, Qt.Key_Right)
    assert voice.tabs.currentIndex() == 1
    voice.tabs.setCurrentIndex(0)
    for combo in (voice.agent_provider, voice.agent_model):
        combo.showPopup()
        QApplication.processEvents()
        QTest.keyClick(combo.view(), Qt.Key_Down)
        QTest.keyClick(combo.view(), Qt.Key_Return)
        assert combo.currentIndex() == 2
        QTest.keyClick(combo, Qt.Key_Up)
        assert combo.currentIndex() == 1


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
    assert not workspace.voice.isHidden()
    workspace.show_panel(3)
    assert not workspace.terminal_dock.isHidden()
    assert workspace.stack.currentIndex() == 2

    workspace.show_panel(1)
    workspace.show_panel(3)
    assert workspace.voice.draft.toPlainText() == "設計を確認"
    assert workspace.console.toPlainText() == "terminal history"
    assert workspace.stack.currentIndex() == 2


@pytest.mark.parametrize("locale", ["en", "ja"])
def test_brand_button_returns_to_sidebar_without_discarding_work(workspace, monkeypatch, locale):
    workspace.voice.set_locale(locale)
    workspace.voice.draft.setPlainText("確認する deployment")
    workspace.console.setPlainText("existing terminal output")
    workspace.show_panel(2)
    editor = workspace.stack.currentWidget()
    page = workspace.web.page()
    calls = []
    monkeypatch.setattr(page, "runJavaScript", lambda script, callback: (calls.append(script), callback(True)))
    workspace.sidebar_button.click()
    assert workspace.stack.currentIndex() == 0
    assert len(calls) == 1 and workspace.sidebar_attempts == 0
    assert workspace.web.page() is page
    assert workspace.voice.draft.toPlainText() == "確認する deployment"
    assert workspace.console.toPlainText() == "existing terminal output"
    assert workspace.sidebar_button.toolTip() == ("Open workspace sidebar" if locale == "en" else "ワークスペースのサイドバーを開く")
    workspace.show_panel(2)
    assert workspace.stack.currentWidget() is editor


def test_sidebar_request_retries_loading_but_does_not_interrupt_another_panel(workspace, monkeypatch):
    callbacks = []
    monkeypatch.setattr(workspace.web.page(), "runJavaScript", lambda script, callback: callbacks.append(callback))
    workspace.sidebar_button.click()
    workspace.sidebar_button.click()
    assert len(callbacks) == 1
    callbacks.pop()(False)
    assert workspace.sidebar_timer.isActive()
    workspace.sidebar_timer.stop()
    workspace.show_panel(2)
    workspace.expand_sidebar()
    assert not callbacks and workspace.stack.currentIndex() == 2


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


def test_tray_close_restore_localize_and_quit(workspace, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    workspace.enable_tray()
    workspace.show()
    workspace.voice.draft.setPlainText("続けて作業")
    workspace.console.setPlainText("saved terminal output")
    cleanup = []
    monkeypatch.setattr(workspace.local_models, "stop_engine", lambda: cleanup.append("engine"))
    workspace.close()
    assert workspace.isHidden() and workspace.tray.isVisible()
    assert not cleanup and not workspace.shutdown_complete
    workspace.tray_activated(QSystemTrayIcon.Trigger)
    assert workspace.isVisible()
    assert workspace.voice.draft.toPlainText() == "続けて作業"
    assert workspace.console.toPlainText() == "saved terminal output"
    workspace.voice.set_locale("en")
    assert workspace.tray_quit.text() == "Quit Kotoba Studio"
    workspace.voice.set_locale("ja")
    assert workspace.tray_quit.text() == "Kotoba Studio を終了"
    workspace.request_quit()
    assert cleanup == ["engine"]
    assert workspace.shutdown_complete and not workspace.tray.isVisible()


def test_tray_cannot_hide_active_capture_and_falls_back_without_tray(workspace, monkeypatch):
    from PySide6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: False)
    workspace.enable_tray()
    assert workspace.tray is None
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    workspace.enable_tray()
    workspace.show()
    workspace.voice.stream = object()
    try:
        workspace.close()
        assert workspace.isVisible() and not workspace.shutdown_complete
        workspace.request_quit()
        assert not workspace.exit_requested and not workspace.shutdown_complete
    finally:
        workspace.voice.stream = None
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: False)
    workspace.close()
    assert workspace.shutdown_complete and not workspace.tray.isVisible()


def test_launch_opens_chat_with_both_docks_hidden(workspace):
    assert workspace.stack.currentIndex() == 0
    assert workspace.voice.isHidden()
    assert workspace.terminal_dock.isHidden()


def test_reduced_motion_persists_and_updates_embedded_chat(workspace):
    from PySide6.QtCore import QEventLoop, QTimer
    window = workspace
    from PySide6.QtWebEngineCore import QWebEnginePage
    previous = window.web.page()
    window.web.setPage(QWebEnginePage(previous.profile(), window.web))
    previous.deleteLater()
    window.web.setHtml('<html><head></head><body><button>Action</button></body></html>')
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    window.web.loadFinished.connect(loop.quit)
    timer.start(5000)
    loop.exec()
    timer.stop()
    window.web.loadFinished.disconnect(loop.quit)
    window.reduce_motion.setChecked(True)
    assert window.voice.preferences.value("ui/reduced_motion", type=bool)
    values = []
    window.web.page().runJavaScript("JSON.stringify({mode:document.documentElement.dataset.kotobaMotion, styles:document.querySelectorAll('#kotoba-motion').length, transition:getComputedStyle(document.querySelector('button')).transitionDuration})", lambda value: (values.append(value), loop.quit()))
    timer.start(5000)
    loop.exec()
    timer.stop()
    import json
    assert values and json.loads(values[0]) == {"mode":"off", "styles":1, "transition":"0s"}
    assert all(reveal.animation is None for reveal in window.reveals)


def test_chat_loading_background_matches_dark_shell(workspace):
    assert workspace.web.page().backgroundColor().name() == "#191a1e"
