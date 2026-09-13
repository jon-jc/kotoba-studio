"""Kotoba desktop container for the full agent web application."""

import os
import json
import codecs
from pathlib import Path
import re
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl, Qt, QSize, QEvent
from PySide6.QtGui import QColor, QFont, QTextCursor, QIcon, QShortcut, QKeySequence, QKeyEvent
from PySide6.QtWidgets import (QApplication, QFileSystemModel, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QSplitter, QStackedWidget,
    QTreeView, QVBoxLayout, QWidget, QToolButton, QComboBox, QDialog, QListWidget, QListWidgetItem, QMenu, QSystemTrayIcon)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from .desktop import Window as VoiceWindow, STYLE
from .harness import runtime_path
from .terminal import powershell_arguments
from .workspace_copy import COPY as SHELL_COPY, translate
from .branding import icon_path, configure_windows_identity
from .local_models_ui import LocalModelsPage
from .design import outline_icon
from .code_view import SourceTabs, ElidedPath, SourceIcons
from .motion import Reveal, web_script, system_reduced_motion
from .agent_workbench import AgentWorkbench


class LocalPage(QWebEnginePage):
    """Keep the embedded app on its owned loopback origin."""
    def __init__(self, profile, parent):
        super().__init__(profile, parent)
        self.origin = None
        self.setBackgroundColor(QColor("#191a1e"))

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if not is_main_frame or url.scheme() == "about":
            return True
        return self.origin is not None and url.host() == "127.0.0.1" and url.port() == self.origin.port()


class Workspace(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tray = None
        self.exit_requested = False
        self.shutdown_complete = False
        self.tray_notice_shown = False
        self.voice = VoiceWindow(embedded=True)
        from .messaging_store import MessagingStore
        from .messaging_gateway import MessagingGateway
        self.messaging = MessagingGateway(MessagingStore(self.voice.home), self)
        self.messaging_shutdown_requested = False
        self.messaging.changed.connect(self.messaging_shutdown_changed)
        self.setWindowTitle("Kotoba Studio · ことば")
        self.setWindowIcon(QIcon(str(icon_path())))
        self.resize(1536, 960)
        self.setMinimumSize(1024, 720)
        self.setStyleSheet(STYLE)
        self.backend = QProcess(self)
        self.backend.setProcessChannelMode(QProcess.MergedChannels)
        self.backend.readyReadStandardOutput.connect(self.backend_output)
        self.backend.errorOccurred.connect(lambda _: self.set_health("failed"))
        self.backend.finished.connect(lambda *_: self.set_health("stopped"))
        self.output = ""
        self.url = None
        self.sidebar_attempts = 0
        self.sidebar_check_pending = False
        self.sidebar_timer = QTimer(self)
        self.sidebar_timer.setSingleShot(True)
        self.sidebar_timer.setInterval(200)
        self.sidebar_timer.timeout.connect(self.expand_sidebar)
        self.console_process = QProcess(self)
        self.console_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.console_process.setProcessChannelMode(QProcess.MergedChannels)
        self.console_process.readyReadStandardOutput.connect(self.console_output)
        self.build()
        self.reveals = [Reveal(widget, lambda: not (self.reduce_motion.isChecked() or system_reduced_motion()))
                        for widget in (self.voice, self.terminal_dock)]
        self.sync_motion()
        self.voice.dock_close_requested.connect(self.close_voice_panel)
        self.voice.locale_changed.connect(self.apply_locale)
        self.voice.draft_handoff.connect(self.handoff_draft)
        self.voice.busy_changed.connect(lambda busy: self.locale_toggle.setEnabled(not busy))
        self.voice.busy_changed.connect(lambda busy: self.access_button.setEnabled(not busy and self.backend.state() == QProcess.Running))
        self.voice.busy_changed.connect(lambda busy: self.workflow_context(self.workflow.current_path) if not busy and self.workflow.current_path else None)
        self.apply_locale(self.voice.locale)
        self.start_backend()
        self.messaging_unread = 0
        self.messaging_timer = QTimer(self)
        self.messaging_timer.setInterval(2000)
        self.messaging_timer.timeout.connect(self.update_messaging_badge)
        self.messaging_timer.start()

    def update_messaging_badge(self):
        unread = sum(self.messaging.store.unread().values())
        label = "Messaging" if self.voice.locale == "en" else "メッセージ"
        self.messaging_action.setText(label + (f" · {unread}" if unread else ""))
        message_button = self.collaboration_buttons["messaging"]
        message_button.setToolTip(label + (f" · {unread}" if unread else ""))
        message_button.setAccessibleName(message_button.toolTip())
        if message_button.property("unread") != bool(unread):
            message_button.setProperty("unread", bool(unread))
            message_button.style().unpolish(message_button)
            message_button.style().polish(message_button)
        if self.tray is not None:
            self.tray.setToolTip("Kotoba Studio" + (f" · {unread} " + ("unread messages" if self.voice.locale == "en" else "件の未読メッセージ") if unread else ""))
            if unread > self.messaging_unread and self.voice.preferences.value("messaging/notify", False, type=bool) and QApplication.activeWindow() is None:
                self.tray.showMessage("Kotoba Studio", f"{unread} " + ("unread messages in Messaging" if self.voice.locale == "en" else "件の未読メッセージがあります"), QSystemTrayIcon.Information, 4000)
        self.messaging_unread = unread

    def build(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        shell = QHBoxLayout()
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        outer.addLayout(shell, 1)
        self.rail = QFrame()
        self.rail.setObjectName("workspace-rail")
        self.rail.setFixedWidth(76)
        side = QVBoxLayout(self.rail)
        side.setContentsMargins(8, 8, 8, 10)
        side.setSpacing(5)
        shell.addWidget(self.rail)
        self.sidebar_button = QPushButton()
        self.sidebar_button.setIcon(self.windowIcon())
        self.sidebar_button.setIconSize(QSize(28, 28))
        self.sidebar_button.setFixedSize(60, 44)
        self.sidebar_button.setObjectName("workspace-brand")
        self.sidebar_button.clicked.connect(self.open_sidebar)
        side.addWidget(self.sidebar_button)
        side.addSpacing(12)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        shell.addLayout(content, 1)
        titlebar = QFrame()
        titlebar.setObjectName("workspace-header")
        titlebar.setFixedHeight(56)
        top = QHBoxLayout(titlebar)
        top.setContentsMargins(20, 8, 18, 8)
        top.setSpacing(14)
        self.view_title = QLabel()
        self.view_title.setObjectName("workspace-title")
        top.addWidget(self.view_title)
        self.project_button = QPushButton()
        self.project_button.setObjectName("workspace-project")
        self.project_button.setIcon(outline_icon("folder"))
        self.project_button.setMaximumWidth(230)
        self.project_button.clicked.connect(self.choose_workspace)
        top.addWidget(self.project_button)
        top.addStretch(1)
        self.command_center = QPushButton()
        self.command_center.setObjectName("command-center")
        self.command_center.setFixedHeight(32)
        self.command_center.setMinimumWidth(190)
        self.command_center.setMaximumWidth(270)
        self.command_center.clicked.connect(self.command_palette)
        top.addWidget(self.command_center)
        self.locale_toggle = QComboBox()
        self.locale_toggle.setObjectName("interface-language")
        self.locale_toggle.setFixedSize(108, 32)
        self.locale_toggle.setAccessibleName("Interface language / 表示言語")
        self.locale_toggle.addItem("English", "en")
        self.locale_toggle.addItem("日本語", "ja")
        self.locale_toggle.currentIndexChanged.connect(self.change_locale)
        top.addWidget(self.locale_toggle)
        content.addWidget(titlebar)
        main = QHBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.access_button = QToolButton()
        self.access_button.setObjectName("workspace-tool")
        self.access_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.access_button.setIcon(outline_icon("shield"))
        self.access_button.setIconSize(QSize(19, 19))
        self.access_button.setFixedSize(60, 48)
        self.access_button.setEnabled(False)
        self.access_button.clicked.connect(self.open_access)
        self.voice_toggle = QPushButton()
        self.voice_toggle.clicked.connect(lambda: self.show_panel(1))
        self.voice_toggle.hide()
        self.stack = QStackedWidget()
        self.chat_profiles = []
        self.chats = AgentWorkbench(self.voice.preferences, self.create_chat_view, self)
        self.web = self.chats.active['view']
        self.chats.active_changed.connect(self.select_chat_view)
        self.chats.created.connect(self.prepare_chat_view)
        self.chats.history_requested.connect(self.open_chat_history)
        self.chats.navigation_changed.connect(self.sync_chat_navigation)
        self.stack.addWidget(self.chats)
        self.stack.addWidget(QWidget())  # Legacy voice navigation index; voice now lives in the dock.
        self.stack.addWidget(self.files_page())
        self.stack.addWidget(QWidget())
        self.terminal_dock = self.terminal_page()
        self.stack.addWidget(self.routing_page())
        self.stack.addWidget(self.plugins_page())
        self.local_models = LocalModelsPage(self)
        self.stack.addWidget(self.local_models)
        from .fleet_workspace import FleetWorkspace
        self.workflow = FleetWorkspace(self.voice.home, self)
        self.workflow.tool_requested.connect(self.workflow_tool)
        self.workflow.context_changed.connect(self.workflow_context)
        self.workflow.runtime.state.connect(lambda _: self.selected_panel(self.stack.currentIndex()))
        self.stack.addWidget(self.workflow)
        self.nav_keys = ["◈  Workspace / 会話", "◉  Voice / 音声", "⌘  Code / コード", "›_  Terminal", "⇄  Routing / 接続", "⊞  Plugins", "▣  Local models"]
        self.nav = []
        for index, icon in enumerate(("agents", "mic", "code", "terminal", "routing", "plugins", "models")):
            button = QToolButton()
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIcon(outline_icon(icon))
            button.setIconSize(QSize(20, 20))
            button.setObjectName("workspace-tool")
            button.setFixedSize(60, 50)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.show_panel(i))
            if index < 4:
                side.addWidget(button)
            else:
                button.setParent(titlebar)
                button.hide()
            self.nav.append(button)
            if index == 0:
                self.api_button = QToolButton()
                self.api_button.setObjectName("workspace-tool")
                self.api_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                self.api_button.setIcon(outline_icon("chat"))
                self.api_button.setFixedSize(60, 50)
                self.api_button.setCheckable(True)
                self.api_button.clicked.connect(lambda: self.workflow_tool("api"))
                side.addWidget(self.api_button)
        separator = QFrame()
        separator.setObjectName("rail-divider")
        separator.setFixedHeight(1)
        side.addSpacing(8)
        side.addWidget(separator)
        side.addSpacing(8)
        self.collaboration_buttons = {}
        for key, icon in (("messaging", "messages"), ("handoff", "handoff")):
            button = QToolButton()
            button.setObjectName("workspace-tool")
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIcon(outline_icon(icon))
            button.setFixedSize(60, 50)
            button.clicked.connect(lambda checked=False, tool=key: self.workflow_tool(tool))
            self.collaboration_buttons[key] = button
            side.addWidget(button)
        side.addStretch(1)
        self.accounts_button = QToolButton()
        self.accounts_button.setObjectName("workspace-tool")
        self.accounts_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.accounts_button.setIcon(outline_icon("account"))
        self.accounts_button.setFixedSize(60, 48)
        self.accounts_button.setEnabled(False)
        self.accounts_button.clicked.connect(self.open_agent_accounts)
        side.addWidget(self.accounts_button)
        side.addWidget(self.access_button)
        self.workspace_menu = QMenu(self)
        self.workspace_actions = []
        for index in (4, 5, 6):
            action = self.workspace_menu.addAction(outline_icon(("routing", "plugins", "models")[index - 4]), "")
            action.triggered.connect(lambda checked=False, i=index: self.show_panel(i))
            self.workspace_actions.append(action)
        self.messaging_action = self.workspace_menu.addAction("Messaging / メッセージ")
        self.messaging_action.triggered.connect(self.open_messaging)
        self.team_action = self.workspace_menu.addAction("Team handoffs / チームの引き継ぎ")
        self.team_action.triggered.connect(lambda: self.voice.open_collaboration())
        self.workspace_menu.addSeparator()
        self.reduce_motion = self.workspace_menu.addAction("Reduce motion / 動きを減らす")
        self.reduce_motion.setCheckable(True)
        self.reduce_motion.setChecked(self.voice.preferences.value("ui/reduced_motion", False, type=bool))
        self.reduce_motion.toggled.connect(self.sync_motion)
        self.more_button = QToolButton()
        self.more_button.setObjectName("workspace-tool")
        self.more_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.more_button.setIcon(outline_icon("settings"))
        self.more_button.setFixedSize(60, 48)
        self.more_button.setPopupMode(QToolButton.InstantPopup)
        self.more_button.setMenu(self.workspace_menu)
        side.addWidget(self.more_button)
        self.workbench = QSplitter(Qt.Horizontal)
        self.workbench.setChildrenCollapsible(False)
        self.editor_area = QSplitter(Qt.Vertical)
        self.editor_area.setChildrenCollapsible(False)
        self.editor_area.addWidget(self.stack)
        self.editor_area.addWidget(self.terminal_dock)
        self.editor_area.setStretchFactor(0, 1)
        self.editor_area.setStretchFactor(1, 0)
        self.editor_area.setSizes([650, 230])
        self.terminal_dock.hide()
        self.workbench.addWidget(self.editor_area)
        self.workbench.addWidget(self.voice)
        self.workbench.setStretchFactor(0, 1)
        self.workbench.setStretchFactor(1, 0)
        self.workbench.setSizes([1040, 420])
        self.voice.hide()
        main.addWidget(self.workbench, 1)
        content.addLayout(main, 1)
        statusbar = QFrame()
        statusbar.setObjectName("statusbar")
        status = QHBoxLayout(statusbar)
        status.setContentsMargins(18, 3, 18, 3)
        self.health_key = "starting"
        self.health = QLabel()
        self.health.setStyleSheet("color:#a4b7ad;font-size:11px")
        status.addWidget(self.health)
        status.addStretch()
        self.locale_scope = QLabel()
        self.locale_scope.setStyleSheet("color:#999daa;font-size:11px")
        self.locale_scope.hide()
        status.addSpacing(18)
        version = QLabel("Kotoba Studio  0.11.1")
        version.setObjectName("micro")
        status.addWidget(version)
        content.addWidget(statusbar)
        self.setCentralWidget(root)
        self.stack.currentChanged.connect(self.selected_panel)
        for sequence, callback in (("Ctrl+K", self.command_palette), ("Ctrl+Shift+V", lambda: self.show_panel(1)),
                                   ("Ctrl+J", lambda: self.show_panel(3)), ("Ctrl+Shift+E", lambda: self.show_panel(2)),
                                   ("Ctrl+Shift+Space", self.record_shortcut), ("Ctrl+F", self.find_in_file)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
        self.selected_panel(0)

    def close_voice_panel(self):
        self.voice.hide()
        self.selected_panel(self.stack.currentIndex())

    def record_shortcut(self):
        if self.voice.global_dictation.enabled:
            self.voice.global_dictation.toggle()
            return
        if self.voice.record_button.isEnabled():
            self.voice.show()
            self.voice.record_button.click()
            self.selected_panel(self.stack.currentIndex())

    def show_panel(self, index):
        if index == 0 and self.workflow.runtime.available:
            self.stack.setCurrentWidget(self.workflow)
            self.workflow.runtime.start()
            self.selected_panel(0)
            return
        if index == 1:
            self.voice.setVisible(self.voice.isHidden())
            self.voice.preferences.setValue("ui/voice_dock", not self.voice.isHidden())
            if not self.voice.isHidden():
                self.workbench.setSizes([max(500, self.width() - 490), 420])
                self.voice.refresh_routes()
        elif index == 3:
            self.terminal_dock.setVisible(self.terminal_dock.isHidden())
            if not self.terminal_dock.isHidden():
                self.editor_area.setSizes([max(300, self.height() - 330), 230])
                self.command.setFocus()
        else:
            if index == 2 and self.stack.currentIndex() == 2:
                self.show_panel(0)
                return
            self.stack.setCurrentIndex(index)
            if self.stack.currentIndex() == 2:
                (self.source_tabs.tabs.currentWidget() or self.tree).setFocus()
        self.selected_panel(self.stack.currentIndex())

    def create_chat_view(self, identity):
        view = QWebEngineView()
        profile = QWebEngineProfile('KotobaHarness' if identity == 'primary' else 'Kotoba-' + identity, self)
        suffix = '' if identity == 'primary' else '/chats/' + identity
        profile.setPersistentStoragePath(str(self.voice.home / ('browser' + suffix)))
        profile.setCachePath(str(self.voice.home / ('browser-cache' + suffix)))
        self.chat_profiles.append(profile)
        self.browser_profile = self.chat_profiles[0]
        view.setPage(LocalPage(profile, view))
        view.destroyed.connect(profile.deleteLater)
        view.setStyleSheet('background:#191a1e')
        return view

    def select_chat_view(self, view):
        self.web = view
        # A delayed voice paste must never cross into a newly selected chat.
        self.pending_handoff = None
        self.sidebar_attempts = 0
        self.sidebar_timer.stop()

    def prepare_chat_view(self, view):
        self.sync_motion()
        self.sync_chat_locale(self.voice.locale)
        self.sync_chat_navigation()

    def sync_chat_navigation(self):
        mode = 'history' if self.chats.history else 'agents'
        source = 'document.documentElement.dataset.kotobaNavigation=' + json.dumps(mode) + ";document.dispatchEvent(new Event('kotoba:navigation'));"
        for entry in self.chats.entries:
            page = entry['view'].page()
            scripts = page.scripts()
            for previous in scripts.find('kotoba-navigation'):
                scripts.remove(previous)
            script = QWebEngineScript()
            script.setName('kotoba-navigation')
            script.setInjectionPoint(QWebEngineScript.DocumentReady)
            script.setWorldId(QWebEngineScript.MainWorld)
            script.setSourceCode(source)
            scripts.insert(script)
            page.runJavaScript(source)

    def selected_panel(self, index):
        in_workflow = self.stack.currentWidget() == self.workflow
        self.access_button.setEnabled(self.workflow.state == "ready" if in_workflow else self.url is not None)
        self.access_button.setToolTip(("Agent CLI permissions" if self.voice.locale == "en" else "エージェント CLI の権限") if in_workflow else ("API harness permissions" if self.voice.locale == "en" else "API ハーネスの権限"))
        if index == self.stack.indexOf(self.workflow):
            index = 0
        self.accounts_button.setEnabled(self.workflow.state == "ready")
        self.routing_accounts_button.setEnabled(self.workflow.state == "ready")
        self.api_button.setChecked(self.stack.currentWidget() == self.chats)
        titles = {0: ("API chat", "API 会話"), 2: ("Code", "コード"), 4: ("Connections", "接続"), 5: ("Plugins", "プラグイン"), 6: ("Local models", "ローカルモデル")}
        title = ("Agents", "エージェント") if in_workflow else titles.get(self.stack.currentIndex(), ("Workspace", "ワークスペース"))
        self.view_title.setText(title[self.voice.locale == "ja"])
        project = self.workflow.current_path if in_workflow else self.voice.workspace
        self.project_button.setText((Path(project).name or project)[:30] if project else ("Open project" if self.voice.locale == "en" else "プロジェクトを開く"))
        self.project_button.setToolTip(project or ("Choose a project" if self.voice.locale == "en" else "プロジェクトを選択"))
        for i, button in enumerate(self.nav):
            active = i == index
            if i == 0:
                active = in_workflow or (not self.workflow.runtime.available and self.stack.currentWidget() == self.chats)
            elif i == 1:
                active = not self.voice.isHidden()
            elif i == 3:
                active = not self.terminal_dock.isHidden()
            button.setChecked(active)

    def open_agent_accounts(self):
        self.show_panel(0)
        self.workflow.navigate("accounts")

    def open_sidebar(self):
        """Return to the retained chat page and expand its existing sidebar."""
        self.show_panel(0)
        if self.stack.currentWidget() == self.workflow:
            self.workflow.navigate("sidebar")
            return
        self.open_chat_history()

    def open_chat_history(self):
        """API history stays with its retained API client, independent of Agents."""
        self.stack.setCurrentWidget(self.chats)
        self.chats.set_history(True)
        self.sidebar_attempts = 50
        self.expand_sidebar()

    def expand_sidebar(self):
        if self.sidebar_check_pending or not self.sidebar_attempts or self.stack.currentIndex() != 0:
            return
        self.sidebar_check_pending = True
        self.sidebar_attempts -= 1
        def revealed(ok):
            self.sidebar_check_pending = False
            if ok:
                self.sidebar_attempts = 0
                self.sidebar_timer.stop()
            elif self.sidebar_attempts and self.stack.currentIndex() == 0:
                self.sidebar_timer.start()
        self.web.page().runJavaScript("""(() => {
            const buttons = [...document.querySelectorAll('button')];
            const find = labels => buttons.find(b => labels.includes(b.getAttribute('aria-label')) && !b.closest('[inert]'));
            const expand = find(['Open sidebar', 'サイドバーを開く', '打开侧边栏']);
            if (expand) { expand.click(); return true; }
            return !!find(['Collapse sidebar', 'サイドバーを閉じる', '收起侧边栏']);
        })()""", revealed)

    def command_palette(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Command center / コマンドセンター")
        dialog.resize(560, 430)
        layout = QVBoxLayout(dialog)
        query = QLineEdit()
        query.setPlaceholderText("Search actions…" if self.voice.locale == "en" else "操作を検索…")
        layout.addWidget(query)
        actions = QListWidget()
        for index, key in enumerate(self.nav_keys):
            item = QListWidgetItem(translate(key, self.voice.locale))
            item.setData(Qt.UserRole, index)
            actions.addItem(item)
        for key, en, ja in (("accounts", "Agent accounts", "エージェントのアカウント"), ("api", "API chat", "API 会話"), ("access", "Access settings", "アクセス設定"), ("project", "Open project", "プロジェクトを開く")):
            item = QListWidgetItem(ja if self.voice.locale == "ja" else en)
            item.setData(Qt.UserRole, key)
            actions.addItem(item)
        team = QListWidgetItem("Team handoffs" if self.voice.locale == "en" else "チームの引き継ぎ")
        team.setData(Qt.UserRole, "team")
        actions.addItem(team)
        messaging = QListWidgetItem("Messaging · LINE / Slack / Discord / Telegram" if self.voice.locale == "en" else "メッセージ · LINE / Slack / Discord / Telegram")
        messaging.setData(Qt.UserRole, "messaging")
        actions.addItem(messaging)
        actions.setCurrentRow(0)
        layout.addWidget(actions)
        def filter_actions(text):
            for row in range(actions.count()):
                item = actions.item(row)
                item.setHidden(text.casefold() not in item.text().casefold())
            for row in range(actions.count()):
                if not actions.item(row).isHidden():
                    actions.setCurrentRow(row)
                    break
        def activate(item):
            if item is not None and not item.isHidden():
                target = item.data(Qt.UserRole)
                dialog.accept()
                if target == "accounts":
                    self.open_agent_accounts()
                elif target == "api":
                    self.workflow_tool("api")
                elif target == "access":
                    self.open_access()
                elif target == "project":
                    self.choose_workspace()
                elif target == "messaging":
                    self.open_messaging()
                elif target == "team":
                    self.voice.open_collaboration()
                else:
                    self.show_panel(target)
        query.textChanged.connect(filter_actions)
        query.returnPressed.connect(lambda: activate(actions.currentItem()))
        actions.itemActivated.connect(activate)
        query.setFocus()
        dialog.exec()

    def change_locale(self):
        self.voice.set_locale(self.locale_toggle.currentData())
        self.apply_locale(self.voice.locale)

    def sync_motion(self, *_):
        reduced = self.reduce_motion.isChecked()
        self.voice.preferences.setValue("ui/reduced_motion", reduced)
        if reduced:
            for reveal in getattr(self, "reveals", []):
                reveal.stop()
        script = QWebEngineScript()
        script.setName("kotoba-motion")
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        source = web_script(reduced or system_reduced_motion())
        script.setSourceCode(source)
        for entry in self.chats.entries:
            scripts = entry['view'].page().scripts()
            for previous in scripts.find("kotoba-motion"):
                scripts.remove(previous)
            scripts.insert(script)
            entry['view'].page().runJavaScript(source)

    def sync_chat_locale(self, locale):
        script = QWebEngineScript()
        script.setName("kotoba-language")
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        source = "document.documentElement.dataset.kotobaLocale=" + json.dumps(locale) + ";document.dispatchEvent(new Event('kotoba:locale'));"
        script.setSourceCode(source)
        for entry in self.chats.entries:
            scripts = entry['view'].page().scripts()
            for previous in scripts.find("kotoba-language"):
                scripts.remove(previous)
            scripts.insert(script)
            entry['view'].page().runJavaScript(source)

    def apply_locale(self, locale):
        """Update shell labels without rebuilding web, terminal, or file state."""
        for widget, en, ja in self.connection_copy:
            widget.setText(ja if locale == "ja" else en)
        self.chats.set_locale(locale)
        self.workflow.set_locale(locale)
        self.sync_chat_navigation()
        self.reduce_motion.setText("Reduce motion" if locale == "en" else "動きを減らす")
        self.sidebar_button.setToolTip("Open workspace sidebar" if locale == "en" else "ワークスペースのサイドバーを開く")
        self.sidebar_button.setAccessibleName(self.sidebar_button.toolTip())
        self.locale_toggle.blockSignals(True)
        self.access_button.setText("Access" if locale == "en" else "アクセス")
        self.accounts_button.setText("Accounts" if locale == "en" else "アカウント")
        self.accounts_button.setToolTip("Connect agent accounts" if locale == "en" else "エージェントのアカウントを接続")
        self.api_button.setText("API chat" if locale == "en" else "API 会話")
        self.api_button.setToolTip("Chats with your configured API providers" if locale == "en" else "設定済みの API プロバイダーとの会話")
        self.api_button.setAccessibleName(self.api_button.text())
        self.collaboration_buttons["messaging"].setText("Messages" if locale == "en" else "メッセージ")
        self.collaboration_buttons["handoff"].setText("Handoffs" if locale == "en" else "引き継ぎ")
        for button in self.collaboration_buttons.values():
            button.setToolTip(button.text())
            button.setAccessibleName(button.text())
        self.more_button.setText("Settings" if locale == "en" else "設定")
        self.project_button.setText("Open project" if locale == "en" else "プロジェクトを開く")
        self.project_button.setToolTip("Choose the project for this workspace" if locale == "en" else "このワークスペースのプロジェクトを選択")
        self.locale_toggle.setCurrentIndex(self.locale_toggle.findData(locale))
        self.locale_toggle.blockSignals(False)
        self.locale_scope.setText(translate("scope", locale))
        self.local_models.set_locale(locale)
        self.source_tabs.set_locale(locale)
        self.code_title.setText("Code" if locale == "en" else "コード")
        self.explorer_title.setText("EXPLORER" if locale == "en" else "エクスプローラー")
        self.code_find.setText("Find in file" if locale == "en" else "ファイル内を検索")
        self.code_find.setToolTip("Ctrl+F")
        self.code_folder.setText("Open folder" if locale == "en" else "フォルダーを開く")
        self.code_close.setText("Close Code  ×" if locale == "en" else "コードを閉じる  ×")
        self.code_close.setToolTip("Return to chat · Esc" if locale == "en" else "会話に戻る · Esc")
        self.code_close.setAccessibleName(self.code_close.text())
        self.update_tray_locale()
        self.command_center.setText("⌕   Search commands…     Ctrl K" if locale == "en" else "⌕   コマンドを検索…     Ctrl K")
        self.voice_toggle.setText("◉ Voice studio" if locale == "en" else "◉ 音声スタジオ")
        for button, key in zip(self.nav, self.nav_keys):
            button.setToolTip(translate(key, locale))
            button.setAccessibleName(translate(key, locale))
        names = ("Chat", "Voice", "Code", "Terminal", "Connections", "Plugins", "Local AI") if locale == "en" else ("会話", "音声", "コード", "ターミナル", "接続", "プラグイン", "ローカル AI")
        for button, name in zip(self.nav, names):
            button.setText(name)
        if self.workflow.runtime.available:
            self.nav[0].setText("Agents" if locale == "en" else "エージェント")
            self.nav[0].setAccessibleName(self.nav[0].text())
            self.nav[0].setToolTip("Subscription agents and worktrees" if locale == "en" else "サブスクリプションのエージェントと作業ツリー")
        self.more_button.setToolTip("Models, routing & plugins" if locale == "en" else "モデル・接続・プラグイン")
        self.more_button.setAccessibleName(self.more_button.toolTip())
        for action, name in zip(self.workspace_actions, names[4:]):
            action.setText(name)
        self.sync_chat_locale(locale)
        for widget in self.centralWidget().findChildren(QWidget):
            if widget == self.voice or self.voice.isAncestorOf(widget):
                continue
            placeholder = isinstance(widget, (QLineEdit, QPlainTextEdit))
            if not placeholder and not isinstance(widget, (QLabel, QPushButton)):
                continue
            text = widget.placeholderText() if placeholder else widget.text()
            key = widget.property("localeSource") or text
            if key in SHELL_COPY:
                widget.setProperty("localeSource", key)
                if placeholder:
                    widget.setPlaceholderText(translate(key, locale))
                else:
                    widget.setText(translate(key, locale))
        self.selected_panel(self.stack.currentIndex())
        if self.health_key:
            self.set_health(self.health_key)

    def open_access(self):
        if self.stack.currentWidget() == self.workflow:
            self.workflow.navigate("permissions")
            return
        if self.url is None or self.voice.job is not None or self.voice.stream is not None:
            return
        from .access_ui import AccessDialog
        self.voice.permission_dialog_active = True
        try:
            dialog = AccessDialog(self)
            dialog.exec()
            dialog.deleteLater()
        finally:
            self.voice.permission_dialog_active = False

    def set_health(self, key):
        self.health_key = key
        self.health.setText(translate(key, self.voice.locale))
        if key in ("failed", "stopped", "timeout"):
            self.access_button.setEnabled(False)

    def handoff_draft(self, text):
        if self.stack.currentWidget() == self.workflow:
            self.workflow.draft(text)
            return
        QApplication.clipboard().setText(text)
        self.stack.setCurrentIndex(0)
        self.web.setFocus()
        self.pending_handoff = object()
        request = self.pending_handoff
        self.web.page().runJavaScript("""(() => {
            const input = document.querySelector('[data-composer-input][contenteditable="true"]');
            if (!input || !input.getClientRects().length) return '';
            input.focus();
            return input.innerText.trim() ? 'append' : 'empty';
        })()""", lambda state: self.paste_reviewed_draft(state, text, request))

    def paste_reviewed_draft(self, state, text, request):
        if self.pending_handoff is not request:
            return
        if state in ("append", "empty") and self.stack.currentIndex() == 0:
            QApplication.clipboard().setText(("\n" if state == "append" else "") + text)
            # Native navigation lets the editor update its own selection before paste.
            for kind in (QEvent.KeyPress, QEvent.KeyRelease):
                QApplication.sendEvent(self.web.focusProxy(), QKeyEvent(kind, Qt.Key_End, Qt.ControlModifier))
            self.web.page().triggerAction(QWebEnginePage.Paste)
            self.set_health("draft_added")
        else:
            self.set_health("paste")

    def find_in_file(self):
        if self.stack.currentIndex() == 2:
            self.source_tabs.show_find()
        else:
            self.web.setFocus()

    def panel(self, title, description):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 14, 18, 14)
        header = QLabel(title)
        header.setStyleSheet("font-size:16px;font-weight:600")
        layout.addWidget(header)
        label = QLabel(description)
        label.setWordWrap(True)
        label.setStyleSheet("color:#999daa;font-size:12px;padding-bottom:8px")
        layout.addWidget(label)
        return widget, layout

    def files_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)
        header = QHBoxLayout()
        self.code_title = QLabel()
        self.code_title.setStyleSheet("font-size:20px;font-weight:600;color:#e8ecea")
        self.code_title.hide()
        header.addStretch()
        self.code_find = QPushButton()
        self.code_find.setObjectName("ghost")
        self.code_find.clicked.connect(self.find_in_file)
        header.addWidget(self.code_find)
        self.code_folder = QPushButton()
        self.code_folder.setIcon(outline_icon("folder"))
        self.code_folder.clicked.connect(self.choose_workspace)
        self.code_folder.hide()
        self.code_close = QPushButton()
        self.code_close.setObjectName("ghost")
        self.code_close.clicked.connect(lambda: self.show_panel(0))
        header.addWidget(self.code_close)
        layout.addLayout(header)
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        explorer = QFrame()
        explorer.setObjectName("code-explorer")
        explorer.setMinimumWidth(200)
        explorer_layout = QVBoxLayout(explorer)
        explorer_layout.setContentsMargins(12, 12, 12, 8)
        explorer_layout.setSpacing(12)
        self.explorer_title = QLabel()
        self.explorer_title.setStyleSheet("font-size:11px;font-weight:600;color:#9ca7b2")
        explorer_layout.addWidget(self.explorer_title)
        self.path_label = ElidedPath(Path(self.voice.workspace).name or self.voice.workspace)
        self.path_label.setToolTip(self.voice.workspace)
        self.path_label.setFixedHeight(24)
        explorer_layout.addWidget(self.path_label)
        self.files = QFileSystemModel(self)
        self.source_icons = SourceIcons()
        self.files.setIconProvider(self.source_icons)
        self.files.setReadOnly(True)
        self.files.setRootPath(self.voice.workspace)
        self.tree = QTreeView()
        self.tree.setModel(self.files)
        self.tree.setRootIndex(self.files.index(self.voice.workspace))
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.clicked.connect(self.view_file)
        explorer_layout.addWidget(self.tree, 1)
        self.source_tabs = SourceTabs()
        self.source_tabs.set_workspace(self.voice.workspace)
        self.source_tabs.setObjectName("code-source")
        self.source_tabs.choose_folder.connect(self.choose_workspace)
        self.source_tabs.tabs.currentChanged.connect(lambda *_: self.code_find.setEnabled(self.source_tabs.tabs.count() > 0))
        self.code_find.setEnabled(False)
        splitter.addWidget(explorer)
        splitter.addWidget(self.source_tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1000])
        layout.addWidget(splitter, 1)
        escape = QShortcut(QKeySequence("Escape"), widget)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(self.escape_code)
        close_tab = QShortcut(QKeySequence("Ctrl+W"), widget)
        close_tab.setContext(Qt.WidgetWithChildrenShortcut)
        close_tab.activated.connect(lambda: self.source_tabs.close_tab(self.source_tabs.tabs.currentIndex())
                                    if self.source_tabs.tabs.count() else self.show_panel(0))
        return widget

    def escape_code(self):
        if not self.source_tabs.find_bar.isHidden():
            self.source_tabs.hide_find()
        else:
            self.show_panel(0)

    def view_file(self, index):
        path = Path(self.files.filePath(index))
        if not path.is_file():
            return
        try:
            if path.stat().st_size > 1024 * 1024:
                self.health_key = None
                self.health.setText(translate("file_large", self.voice.locale))
                return
            content = path.read_text(encoding="utf-8")
            if "\x00" in content:
                raise UnicodeError("Binary file")
            self.source_tabs.open_file(path, content)

        except (OSError, UnicodeError):
            self.health_key = None
            self.health.setText(translate("file_invalid", self.voice.locale))

    def terminal_page(self):
        widget, layout = self.panel("Terminal / ターミナル", "Local PowerShell command console. For interactive PTY sessions, use the terminal tools in the Kotoba Studio workspace.")
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console.setStyleSheet('font-family:"Consolas";font-size:13px;')
        self.console.setMaximumBlockCount(5000)
        layout.addWidget(self.console, 1)
        self.command = QLineEdit()
        self.command.setPlaceholderText("PowerShell command · Enter to run")
        self.command.returnPressed.connect(self.run_command)
        layout.addWidget(self.command)
        return widget

    def run_command(self):
        command = self.command.text().strip()
        if not command:
            return
        if self.console_process.state() == QProcess.NotRunning:
            self.console_process.setWorkingDirectory(self.voice.workspace)
            self.console_decoder.reset()
            self.console_process.start("powershell.exe", powershell_arguments())
            if not self.console_process.waitForStarted(3000):
                self.console.appendPlainText(translate("terminal_failed", self.voice.locale))
                return
        self.console_process.write((command + "\n").encode("utf-8"))
        self.command.clear()

    def console_output(self):
        text = self.console_decoder.decode(bytes(self.console_process.readAllStandardOutput()))
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.console.setTextCursor(cursor)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def routing_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(18)
        self.connection_copy = []
        def label(en, ja, kind="muted"):
            text = QLabel(en)
            text.setObjectName(kind)
            text.setWordWrap(True)
            self.connection_copy.append((text, en, ja))
            return text
        layout.addWidget(label("Connect your AI", "AI を接続", "hero"))
        layout.addWidget(label("Choose how you want to work. Each connection stays independent.", "使い方に合わせて接続を選択します。それぞれの接続は独立して管理されます。"))
        for icon, title, title_ja, description, description_ja, action, action_ja, callback in [
            ("account", "Subscription agents", "サブスクリプションのエージェント", "Use your Codex, Claude Code, OpenCode or Pi account for project work.", "Codex・Claude Code・OpenCode・Pi のアカウントでプロジェクトを進めます。", "Manage agent accounts", "エージェントのアカウントを管理", self.open_agent_accounts),
            ("routing", "API providers", "API プロバイダー", "Connect API keys, discover models, and choose a provider in each chat.", "API キーを接続してモデルを取得し、チャットごとにプロバイダーを選択します。", "Configure API providers", "API プロバイダーを設定", lambda: self.open_settings("models")),
            ("models", "Local models", "ローカルモデル", "Load a GGUF model or connect a local Ollama or LM Studio server.", "GGUF モデルを読み込むか、ローカルの Ollama・LM Studio に接続します。", "Open local models", "ローカルモデルを開く", lambda: self.show_panel(6)),
        ]:
            card = QFrame()
            card.setObjectName("connection-card")
            box = QHBoxLayout(card)
            box.setContentsMargins(22, 20, 22, 20)
            details = QVBoxLayout()
            details.setSpacing(8)
            heading = label(title, title_ja)
            heading.setStyleSheet("font-size:15px;font-weight:600;color:#e8eaef")
            details.addWidget(heading)
            details.addWidget(label(description, description_ja))
            box.addLayout(details, 1)
            button = QPushButton(action)
            button.setIcon(outline_icon(icon))
            button.clicked.connect(callback)
            self.connection_copy.append((button, action, action_ja))
            if icon == "account":
                self.routing_accounts_button = button
            box.addWidget(button)
            layout.addWidget(card)
        audio = QPushButton()
        self.connection_copy.append((audio, "Voice model and agent settings", "音声モデルとエージェントの設定"))
        audio.setObjectName("ghost")
        audio.clicked.connect(self.voice.settings)
        layout.addWidget(audio, 0, Qt.AlignLeft)
        layout.addStretch(1)
        return widget

    def plugins_page(self):
        widget, layout = self.panel("Plugin workspace / プラグイン", "The original Cordis plugin architecture remains intact. Inspect active plugins and model adapters in Kotoba Studio Settings → Plugins.")
        description = QLabel("Tools · Agent presets · Model adapters · Skills · Subagents · Workflows\n\nUse the upstream plugin interface to inspect the complete composition. External plugin installation follows the dsh profile workflow and requires pnpm. Plugins execute code with the runtime's access; inspect their source before installing.")
        description.setWordWrap(True)
        layout.addWidget(description)
        button = QPushButton("Open full Kotoba Studio workspace  →")
        button.clicked.connect(lambda: self.open_settings("plugins"))
        layout.addWidget(button)
        layout.addStretch()
        return widget

    def open_settings(self, section):
        """Navigate existing upstream controls; credentials stay in their owning UI."""
        self.stack.setCurrentIndex(0)
        labels = {"models": ["Models", "模型", "モデル"], "plugins": ["Plugins", "插件", "プラグイン"]}[section]
        script = """(() => {
            const buttons = () => Array.from(document.querySelectorAll('button'));
            const find = labels => buttons().find(b => labels.includes(b.textContent.trim()));
            const trigger = find(['Settings', '设置', '設定']);
            if (!trigger || trigger.closest('[inert]')) return false;
            if (trigger.getAttribute('aria-expanded') !== 'true') trigger.click();
            return true;
        })()"""
        def opened(ok):
            if ok:
                QTimer.singleShot(200, lambda: self.web.page().runJavaScript(
                    "Array.from(document.querySelectorAll('button')).find(b => " + json.dumps(labels) + ".includes(b.textContent.trim()))?.click()"))
            else:
                self.set_health("setup")
        self.web.page().runJavaScript(script, opened)

    def choose_workspace(self):
        path = QFileDialog.getExistingDirectory(self, "Workspace / 作業フォルダー", self.voice.workspace)
        if path:
            if self.stack.currentWidget() == self.workflow:
                self.workflow.add_project(path)
                return
            self.voice.workspace = path
            self.files.setRootPath(path)
            self.tree.setRootIndex(self.files.index(path))
            self.path_label.setText(Path(path).name or path)
            self.path_label.setToolTip(path)
            self.source_tabs.set_workspace(path)
            self.stack.setCurrentIndex(2)

    def start_backend(self):
        try:
            runtime = runtime_path()
        except FileNotFoundError as error:
            self.health_key = None
            self.health.setText(str(error))
            return
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("DSH_HOME", str(self.voice.home / "harness"))
        environment.insert("DSH_TELEMETRY_DISABLED", "1")
        self.backend.setProcessEnvironment(environment)
        self.backend.setWorkingDirectory(self.voice.workspace)
        args = ["--profile", "web", "--patch", str(icon_path().parent / "desktop-workspace.patch.yml"),
                "--no-open", "--host", "127.0.0.1", "--port", "0"]
        if runtime.suffix == ".js":
            self.backend.start("node", [str(runtime), *args])
        else:
            self.backend.start(str(runtime), args)
        QTimer.singleShot(60000, self.startup_deadline)
        if self.workflow.runtime.available:
            self.show_panel(0)

    def workflow_context(self, path):
        if self.voice.job is not None:
            return
        self.voice.workspace = path
        self.files.setRootPath(path)
        self.tree.setRootIndex(self.files.index(path))
        self.path_label.setText(Path(path).name or path)
        self.path_label.setToolTip(path)
        self.source_tabs.set_workspace(path)
        self.project_button.setText((Path(path).name or path)[:30])
        self.project_button.setToolTip(path)

    def workflow_tool(self, tool):
        if self.workflow.current_path:
            self.workflow_context(self.workflow.current_path)
        if tool == "accounts":
            self.workflow.navigate("accounts")
        elif tool == "api":
            self.stack.setCurrentIndex(0)
            self.selected_panel(0)
        elif tool == "voice":
            self.show_panel(1)
        elif tool == "handoff":
            self.voice.open_collaboration()
        elif tool == "messaging":
            self.open_messaging()

    def startup_deadline(self):
        if self.url is None and self.backend.state() != QProcess.NotRunning:
            self.set_health("timeout")
            self.backend.kill()

    def backend_output(self):
        self.output = (self.output + bytes(self.backend.readAllStandardOutput()).decode("utf-8", errors="replace"))[-16000:]
        match = re.search(r"http://127\.0\.0\.1:\d+(?:/\?token=[A-Za-z0-9_-]+)?", self.output)
        if match and self.url is None:
            self.url = QUrl(match.group())
            self.chats.load(self.url)
            self.voice.runtime_url = self.url.toString()
            self.voice.refresh_routes()
            self.set_health("connected")

    def enable_tray(self):
        """Keep the app available after closing only when the OS exposes a tray."""
        if self.tray is not None or not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Kotoba Studio · ことば")
        self.tray_menu = QMenu(self)
        self.tray_show = self.tray_menu.addAction(self.windowIcon(), "")
        self.tray_show.triggered.connect(self.restore_from_tray)
        self.tray_voice = self.tray_menu.addAction(outline_icon("mic"), "")
        self.tray_voice.triggered.connect(self.open_voice_from_tray)
        self.tray_menu.addSeparator()
        self.tray_quit = self.tray_menu.addAction("")
        self.tray_quit.triggered.connect(self.request_quit)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.messageClicked.connect(self.restore_from_tray)
        self.update_tray_locale()
        self.tray.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def update_tray_locale(self):
        if self.tray is not None:
            en = self.voice.locale == "en"
            self.tray_show.setText("Open Kotoba Studio" if en else "Kotoba Studio を開く")
            self.tray_voice.setText("Open Voice Studio" if en else "音声スタジオを開く")
            self.tray_quit.setText("Quit Kotoba Studio" if en else "Kotoba Studio を終了")

    def restore_from_tray(self):
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_voice_from_tray(self):
        self.restore_from_tray()
        if self.voice.isHidden():
            self.show_panel(1)
        self.voice.draft.setFocus()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.restore_from_tray()

    def open_messaging(self):
        from .messaging_ui import MessagingDialog
        dialog = MessagingDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def messaging_shutdown_changed(self):
        if self.messaging_shutdown_requested and not self.messaging.running:
            self.messaging_shutdown_requested = False
            QTimer.singleShot(0, self.request_quit)

    def request_quit(self):
        self.exit_requested = True
        self.close()
        if self.shutdown_complete:
            QApplication.instance().quit()
        else:
            self.exit_requested = False

    def closeEvent(self, event):
        if self.shutdown_complete:
            event.accept()
            return
        if getattr(self.voice, "permission_dialog_active", False):
            event.ignore()
            return
        if self.voice.job is not None or self.voice.stream is not None or self.local_models.job is not None:
            self.restore_from_tray()
            self.voice.show()
            self.voice.status.setText(self.voice.t("busy_close"))
            event.ignore()
            return
        if not self.exit_requested and self.tray is not None and self.tray.isVisible() and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
            if not self.tray_notice_shown:
                self.tray_notice_shown = True
                message = "Still running in the system tray. Use the tray menu to open or quit." if self.voice.locale == "en" else "トレイで実行中です。トレイのメニューから開くか終了できます。"
                self.tray.showMessage("Kotoba Studio", message, QSystemTrayIcon.Information, 4000)
            return
        if self.messaging.running:
            self.messaging_shutdown_requested = True
            self.messaging.stop()
            event.ignore()
            return
        if self.tray is not None:
            self.tray.hide()
        self.messaging_timer.stop()
        self.workflow.shutdown()
        self.voice.close()
        self.chats.shutdown()
        self.local_models.stop_engine()
        for process in (self.console_process, self.backend):
            if process.state() != QProcess.NotRunning:
                if sys.platform == "win32":
                    # Limit termination to this app's live process and its children.
                    QProcess.execute("taskkill.exe", ["/PID", str(process.processId()), "/T", "/F"])
                else:
                    process.terminate()
                if not process.waitForFinished(2000):
                    process.kill()
                    process.waitForFinished(2000)
        self.shutdown_complete = True
        event.accept()
        if self.tray is not None:
            QApplication.instance().quit()


def main():
    configure_windows_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("Kotoba")
    app.setOrganizationName("Kotoba")
    app.setApplicationDisplayName("Kotoba Studio")
    app.setWindowIcon(QIcon(str(icon_path())))
    window = Workspace()
    if "--smoke" not in sys.argv or "--tray-smoke" in sys.argv:
        window.enable_tray()
    window.show()
    if "--workspace-smoke" in sys.argv:
        from .workspace_smoke import verify
        verify(window)
        sys.exit(app.exec())
    if "--smoke" in sys.argv:
        completed = False
        def check():
            if not completed:
                window.web.page().runJavaScript("JSON.stringify({title:document.title, buttons:document.querySelectorAll('button').length, batches:window.__DSH_BOOT__?.batches?.length || 0, failed:document.body.innerText.includes('Failed to load plugins')})", result)
        def result(raw):
            nonlocal completed
            if completed or not raw:
                return
            state = json.loads(raw)
            if state["buttons"] < 1 or state["batches"] < 1 or state["failed"] or "Kotoba Studio" not in state["title"]:
                return
            completed = True
            screenshot = Path(os.environ.get("KOTOBA_SCREENSHOT", "kotoba-workspace.png"))
            original_locale = window.voice.locale
            pending = iter(("en", "ja"))
            evidence = {}
            def switch_next():
                locale = next(pending, None)
                if locale is None:
                    window.locale_toggle.setCurrentIndex(window.locale_toggle.findData(original_locale))
                    window.grab().save(str(screenshot))
                    source = window.voice.home / "smoke-source.py"
                    content = "message = '日本語 / English'\nprint(message)\n"
                    source.write_text(content, encoding="utf-8")
                    window.source_tabs.open_file(source, content)
                    editor = window.source_tabs.tabs.currentWidget()
                    highlighted = bool(editor.highlighter.lines)
                    if not highlighted:
                        window.request_quit()
                        app.exit(1)
                        return
                    window.stack.setCurrentIndex(2)
                    app.processEvents()
                    window.grab().save(str(screenshot.with_name(screenshot.stem + "-source.png")))
                    window.stack.setCurrentIndex(6)
                    app.processEvents()
                    window.grab().save(str(screenshot.with_name(screenshot.stem + "-local-models.png")))
                    tray_checks = {}
                    if "--tray-smoke" in sys.argv:
                        tray_checks["available"] = window.tray is not None and window.tray.isVisible()
                        window.close()
                        tray_checks["background_runtime"] = window.isHidden() and not window.shutdown_complete and window.backend.state() == QProcess.Running
                        if window.tray is not None:
                            window.tray_show.trigger()
                            tray_checks["restore"] = window.isVisible()
                            tray_checks["branded_icon"] = not window.tray.icon().isNull() and window.tray.icon().cacheKey() == window.windowIcon().cacheKey()
                        if not all(tray_checks.values()):
                            window.request_quit()
                            app.exit(1)
                            return
                    screenshot.with_suffix(".json").write_text(json.dumps({"runtime_ready": True, "locale_toggle": True, "source_highlighting": highlighted,
                        "chat_locales": evidence, "tray": tray_checks, **state}), encoding="utf-8")
                    window.request_quit()
                    return
                window.locale_toggle.setCurrentIndex(window.locale_toggle.findData(locale))
                def inspected(raw):
                    value = json.loads(raw)
                    if value["lang"] != locale or value["notice"]:
                        window.request_quit()
                        app.exit(1)
                        return
                    if value["providers"] and not {"openai", "anthropic", "moonshotai"}.issubset(value["providers"]):
                        window.request_quit()
                        app.exit(1)
                        return
                    evidence[locale] = value["lang"]
                    window.grab().save(str(screenshot.with_name(screenshot.stem + "-" + locale + ".png")))
                    switch_next()
                QTimer.singleShot(1000, lambda: window.web.page().runJavaScript(
                    "JSON.stringify({lang:document.documentElement.lang,notice:!![...document.querySelectorAll('[role=dialog]')].find(x=>/Internal Testing Notice|内测声明/.test(x.textContent)),providers:[...document.querySelectorAll('[role=dialog] select option')].map(x=>x.value)})", inspected))
            switch_next()
        timer = QTimer(window)
        timer.timeout.connect(check)
        timer.start(1000)
        def deadline():
            if not completed:
                window.request_quit()
                app.exit(1)
        QTimer.singleShot(70000, deadline)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
