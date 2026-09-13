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
    monkeypatch.setattr("kotoba.fleet_runtime.fleet_location", lambda: tmp_path / "missing-runtime")
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


def test_subscription_workspace_is_primary_and_code_returns_to_it(workspace, monkeypatch):
    from kotoba.fleet_runtime import FleetRuntime
    window = workspace
    monkeypatch.setattr(FleetRuntime, "available", property(lambda self: True))
    commands = []
    monkeypatch.setattr(window.workflow.runtime, "start", lambda: None)
    monkeypatch.setattr(window.workflow.runtime, "request", lambda operation, value, callback=None: commands.append((operation, value)))
    window.show_panel(0)
    assert window.stack.currentWidget() is window.workflow
    window.open_sidebar()
    assert commands[-1] == ("navigate", "sidebar")
    window.show_panel(2)
    window.show_panel(2)
    assert window.stack.currentWidget() is window.workflow
    window.open_access()
    assert commands[-1] == ("navigate", "permissions")
    window.workflow_tool("api")
    assert window.stack.currentWidget() is window.chats


def test_voice_context_waits_for_active_job(workspace, tmp_path):
    window = workspace
    previous = window.voice.workspace
    window.voice.job = object()
    window.workflow.current_path = str(tmp_path)
    window.workflow_context(str(tmp_path))
    assert window.voice.workspace == previous
    window.voice.job = None
    window.voice.busy_changed.emit(False)
    assert window.voice.workspace == str(tmp_path)


def test_parallel_chat_views_keep_independent_storage_and_focus(workspace):
    from PySide6.QtWidgets import QApplication
    window = workspace
    first = window.web
    second = window.chats.add()
    assert window.web is second
    assert first.page().profile() is not second.page().profile()
    assert first.page().profile().persistentStoragePath() != second.page().profile().persistentStoragePath()
    window.chats.list.setCurrentRow(0)
    assert window.web is first
    assert window.chats.entries[1]['view'] is second
    assert window.chats.pages.count() == 2
    assert window.chats.pages.currentWidget() is first
    assert second.isHidden()
    window.chats.list.setCurrentRow(1)
    assert window.chats.pages.currentWidget() is second
    assert first.isHidden()
    assert not hasattr(window.chats, 'split_button')
    assert window.web is second
    window.chats.close_view(1)
    QApplication.processEvents()
    assert window.web is first
    assert len(window.chats.entries) == 1


def test_parallel_agent_status_is_independent_and_late_callbacks_are_ignored(workspace):
    chats = workspace.chats
    chats.set_locale('en')
    first = chats.entries[0]
    chats.add()
    second = chats.entries[1]
    for entry, provider in ((first, 'openai'), (second, 'anthropic')):
        chats.update_state(entry, {'ready': True, 'settled': True, 'session': provider, 'running': True,
                                  'title': provider, 'provider': provider, 'model': 'test-model'})
    assert first['running'] and second['running']
    assert '2 agents running' in chats.context.text()
    chats.update_state(first, {'ready': True, 'settled': True, 'session': 'openai', 'running': False, 'title': 'Review'})
    assert first['unread'] and second['running']
    chats.list.setCurrentRow(0)
    assert not first['unread']
    chats.close_view(1)
    chats.update_state(second, {'running': True, 'title': 'late callback'})
    assert len(chats.entries) == 1 and not first['running']


def test_chat_switch_cancels_pending_voice_paste_and_localizes_all_views(workspace):
    window = workspace
    first = window.web
    window.pending_handoff = object()
    second = window.chats.add()
    assert window.pending_handoff is None
    window.apply_locale('ja')
    assert '新しいエージェント' in window.chats.add_button.text()
    for view in (first, second):
        scripts = view.page().scripts().find('kotoba-language')
        assert len(scripts) == 1 and '"ja"' in scripts[0].sourceCode()


def test_agent_selection_is_saved_only_after_host_list_is_ready(workspace):
    import json
    chats = workspace.chats
    entry = chats.entries[0]
    chats.update_state(entry, {'ready': True, 'settled': True, 'session': 'retained-session', 'running': True})
    saved = json.loads(chats.preferences.value('agents/views'))
    assert saved[0]['session'] == 'retained-session'
    chats.update_state(entry, {'ready': True, 'settled': False, 'session': '', 'running': False})
    assert json.loads(chats.preferences.value('agents/views'))[0]['session'] == 'retained-session'
    scripts = entry['view'].page().scripts().find('kotoba-selection')
    assert len(scripts) == 1
    assert 'retained-session' in scripts[0].sourceCode()
    chats.update_state(entry, {'ready': True, 'settled': True, 'session': '', 'running': False})
    assert json.loads(chats.preferences.value('agents/views'))[0]['session'] == ''


def test_child_selection_retains_its_parent_address(workspace):
    import json
    chats = workspace.chats
    entry = chats.entries[0]
    address = {'parentSessionId': 'parent', 'childSessionId': 'child', 'mode': 'continuable'}
    chats.update_state(entry, {'ready': True, 'settled': True, 'session': 'child', 'address': address})
    saved = json.loads(chats.preferences.value('agents/views'))[0]
    assert saved['address'] == address
    script = entry['view'].page().scripts().find('kotoba-selection')[0].sourceCode()
    assert 'subagentAddress' in script and 'parent' in script
    assert chats.child_address({**address, 'childSessionId': 'other'}, 'child') is None


def test_agent_search_does_not_change_the_active_conversation(workspace):
    chats = workspace.chats
    first = chats.entries[0]
    first['label'] = 'Implementation'
    chats.add(label='Review')
    current = workspace.web
    chats.search.setText('Implementation')
    assert not chats.list.item(0).isHidden()
    assert chats.list.item(1).isHidden()
    assert workspace.web is current
    chats.search.clear()
    assert not chats.list.item(1).isHidden()


def test_history_replaces_agent_roster_and_returns_without_reloading(workspace):
    window = workspace
    page = window.web.page()
    window.open_sidebar()
    assert window.chats.history and window.chats.sidebar.isHidden()
    assert not window.chats.back_button.isHidden()
    window.chats.back_button.click()
    assert not window.chats.history and not window.chats.sidebar.isHidden()
    assert window.web.page() is page
    scripts = page.scripts().find('kotoba-navigation')
    assert len(scripts) == 1 and 'agents' in scripts[0].sourceCode()


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


@pytest.mark.parametrize("locale", ["en", "ja"])
def test_code_can_close_and_reopen_without_losing_tabs(workspace, tmp_path, locale):
    workspace.voice.set_locale(locale)
    path = tmp_path / "example.py"
    workspace.source_tabs.open_file(path, "answer = 42\n")
    editor = workspace.source_tabs.tabs.currentWidget()
    workspace.nav[2].click()
    assert workspace.stack.currentIndex() == 2
    workspace.nav[2].click()
    assert workspace.stack.currentIndex() == 0 and not workspace.nav[2].isChecked()
    workspace.nav[2].click()
    workspace.code_close.click()
    assert workspace.stack.currentIndex() == 0
    workspace.nav[2].click()
    assert workspace.source_tabs.tabs.currentWidget() is editor
    workspace.code_find.click()
    assert not workspace.source_tabs.find_bar.isHidden()
    workspace.escape_code()
    assert workspace.source_tabs.find_bar.isHidden() and workspace.stack.currentIndex() == 2
    workspace.escape_code()
    assert workspace.stack.currentIndex() == 0
    assert editor.toPlainText() == "answer = 42\n"


def test_last_code_tab_returns_to_clean_empty_state(workspace, tmp_path):
    tabs = workspace.source_tabs
    assert tabs.find_bar.isHidden() and not workspace.code_find.isEnabled()
    tabs.open_file(tmp_path / "file.py", "print('hello')\n")
    assert workspace.code_find.isEnabled()
    tabs.show_find()
    tabs.close_tab(0)
    assert tabs.tabs.count() == 0 and not tabs.empty.isHidden()
    assert tabs.find_bar.isHidden() and tabs.position.isHidden() and tabs.breadcrumb.isHidden()
    assert not workspace.code_find.isEnabled()
    tabs.close_tab(-1)


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


def test_voice_prefers_configured_provider_without_carrying_old_model(workspace):
    voice = workspace.voice
    voice.provider = "deepseek-official"
    voice.model = "deepseek-v4-flash"
    voice.api_key = ""
    routes = [
        {"id": "openai", "name": "OpenAI", "configured": True, "models": [{"id": "gpt-fixture"}]},
        {"id": "deepseek-official", "name": "DeepSeek", "configured": False, "models": [{"id": "deepseek-v4-flash"}]},
    ]
    voice.apply_routes(routes)
    assert voice.provider == "openai" and voice.model == "gpt-fixture"
    voice.model = "custom-openai-model"
    voice.preferences.setValue("voice/model_provider", "openai")
    voice.apply_routes(routes)
    assert voice.model == "custom-openai-model"


def test_team_handoffs_workspace_entry_and_meeting_copy(workspace, monkeypatch):
    from kotoba.collaboration import CollaborationStore
    from kotoba.meetings_ui import MeetingsDialog
    seen = []
    monkeypatch.setattr(workspace.voice, "open_collaboration", lambda identity=None: seen.append(identity))
    workspace.team_action.trigger()
    assert seen == [None]
    identity = workspace.voice.meeting_store.create("Bilingual planning")
    workspace.voice.meeting_store.notes(identity, "QA approval is pending. QA の承認待ちです。")
    workspace.voice.meeting_store.finish(identity)
    dialog = MeetingsDialog(workspace.voice)
    try:
        dialog.selected = identity
        dialog.bilingual_handoff()
        _, document = CollaborationStore(workspace.voice.home / "collaboration.sqlite3").read(seen[-1])
        assert document["title"] == "Bilingual planning"
        assert "QA の承認待ちです。" in document["source"]
        workspace.voice.meeting_store.notes(identity, "Edited after import")
        assert "Edited after import" not in document["source"]
    finally:
        dialog.close()
        dialog.deleteLater()


def test_messaging_line_first_inbox_drafts_and_markup_are_plain(workspace):
    from kotoba.messaging_ui import MessagingDialog
    from kotoba.messaging_adapters import message
    from kotoba.messaging_store import PLATFORMS
    from PySide6.QtCore import Qt
    user = "U" + "a" * 32
    dialog = MessagingDialog(workspace)
    try:
        assert dialog.platforms.item(0).data(Qt.UserRole) == "line"
        assert [dialog.platforms.item(i).data(Qt.UserRole) for i in range(4)] == list(PLATFORMS)
        dialog.users.setText(user)
        dialog.token.setText("fixture-token")
        dialog.secret.setText("fixture-secret")
        dialog.save()
        assert dialog.identity
        workspace.messaging.states[dialog.identity] = "Connected"
        dialog.gateway_changed()
        assert "Stopped" in dialog.connection_state.text() or "停止" in dialog.connection_state.text()
        assert dialog.token.text() == "" and dialog.secret.text() == ""
        workspace.messaging.store.ingest(dialog.identity, [message("1", user, user, '<img src="https://invalid.example/track"> 日本語')])
        dialog.refresh_inbox()
        dialog.conversations.setCurrentRow(0)
        assert '<img src="https://invalid.example/track">' in dialog.transcript.toPlainText()
        dialog.draft.setPlainText("確認します。")
        assert workspace.messaging.store.draft(dialog.identity, user) == "確認します。"
        assert not dialog.send_button.isEnabled()
        dialog.load_platform()
        dialog.conversations.setCurrentRow(0)
        assert dialog.draft.toPlainText() == "確認します。"
    finally:
        dialog.close()
        dialog.deleteLater()


def test_messaging_ai_reply_is_bound_to_origin_and_newer_context(workspace):
    from kotoba.messaging_ui import MessagingDialog
    from kotoba.messaging_adapters import message
    user = "U" + "a" * 32
    workspace.voice.apply_routes([dict(id="openai", name="OpenAI", configured=True, key_ref="fixture-ref", models=[dict(id="fixture-model")])])
    dialog = MessagingDialog(workspace)
    try:
        dialog.users.setText(user)
        dialog.token.setText("fixture-token")
        dialog.secret.setText("fixture-secret")
        dialog.save()
        workspace.messaging.store.ingest(dialog.identity, [message("1", user, user, "いつ確認できますか？")])
        dialog.refresh_inbox()
        dialog.conversations.setCurrentRow(0)
        workspace.voice.draft.clear()
        dialog.prepare_ai()
        prompt = workspace.voice.draft.toPlainText()
        assert "Do not execute tools" in prompt and "いつ確認できますか？" in prompt
        workspace.voice.entries.append(dict(kind="turn", prompt=prompt, reply="確認後に連絡します。"))
        dialog.use_ai()
        assert dialog.draft.toPlainText() == "確認後に連絡します。"
        assert workspace.messaging.store.history(dialog.identity, user)[-1]["direction"] == "in"
        workspace.messaging.store.ingest(dialog.identity, [message("2", user, user, "状況が変わりました。")])
        dialog.use_ai()
        assert "changed" in dialog.notice.text() or "更新" in dialog.notice.text()
    finally:
        dialog.close()
        dialog.deleteLater()


def test_messaging_reply_uses_fresh_sdk_session_and_closes_on_failure(workspace, monkeypatch):
    from kotoba import desktop
    voice = workspace.voice
    voice.apply_routes([dict(id="openai", name="OpenAI", configured=True, key_ref="fixture-ref", models=[dict(id="fixture-model")])])
    instances = []
    class Isolated:
        def __init__(self, home):
            self.closed = False
            instances.append(self)
        def run(self, *args, **kwargs):
            if len(instances) == 3:
                raise RuntimeError("fixture failure")
            return object()
        def close(self):
            self.closed = True
    monkeypatch.setattr(desktop, "HarnessSession", Isolated)
    monkeypatch.setattr(voice.harness, "run", lambda *args, **kwargs: pytest.fail("Messaging reused the normal voice SDK session"))
    monkeypatch.setattr(voice, "work", lambda task, result: task(lambda event: None))
    voice.isolated_reply = True
    voice.draft.setPlainText("Prepare a reply to this conversation")
    voice.send()
    voice.send()
    with pytest.raises(RuntimeError, match="fixture failure"):
        voice.send()
    assert len(instances) == 3 and all(instance.closed for instance in instances)

def test_quiet_header_and_left_navigation_fit_both_languages(workspace):
    from PySide6.QtWidgets import QApplication
    window = workspace
    window.resize(1024, 760)
    window.show()
    for locale in ('en', 'ja'):
        window.voice.set_locale(locale)
        QApplication.processEvents()
        assert window.rail.width() == 76
        assert window.rail.isAncestorOf(window.nav[0])
        assert window.rail.isAncestorOf(window.access_button)
        assert not window.rail.isAncestorOf(window.locale_toggle)
        controls = [window.view_title, window.project_button, window.command_center, window.locale_toggle]
        for left, right in zip(controls, controls[1:]):
            assert left.geometry().right() < right.geometry().left()
        assert window.locale_toggle.geometry().right() < window.locale_toggle.parentWidget().width()
        assert not any(button.isVisible() for button in window.workflow.buttons.values())


def test_direct_api_navigation_and_voice_close_keep_work(workspace, monkeypatch):
    from kotoba.fleet_runtime import FleetRuntime
    window = workspace
    monkeypatch.setattr(FleetRuntime, 'available', property(lambda self: True))
    monkeypatch.setattr(window.workflow.runtime, 'start', lambda: None)
    window.show_panel(0)
    assert window.nav[0].isChecked() and not window.api_button.isChecked()
    window.api_button.click()
    assert window.stack.currentWidget() is window.chats
    assert window.api_button.isChecked() and not window.nav[0].isChecked()
    window.voice.draft.setPlainText('明日のレビュー / review tomorrow')
    window.show_panel(1)
    window.voice.dock_close_requested.emit()
    assert window.voice.isHidden() and not window.nav[1].isChecked()
    assert window.voice.draft.toPlainText() == '明日のレビュー / review tomorrow'


def test_accounts_from_code_and_project_label_after_language_change(workspace, monkeypatch, tmp_path):
    from kotoba.fleet_runtime import FleetRuntime
    window = workspace
    monkeypatch.setattr(FleetRuntime, 'available', property(lambda self: True))
    monkeypatch.setattr(window.workflow.runtime, 'start', lambda: None)
    calls = []
    monkeypatch.setattr(window.workflow, 'navigate', calls.append)
    window.workflow.current_path = str(tmp_path)
    window.workflow_context(str(tmp_path))
    window.show_panel(2)
    window.open_agent_accounts()
    assert window.stack.currentWidget() is window.workflow and calls == ['accounts']
    window.voice.set_locale('ja')
    assert window.project_button.toolTip() == str(tmp_path)
    assert window.project_button.text() == tmp_path.name[:30]
