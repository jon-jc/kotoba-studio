"""Kotoba desktop container for the full agent web application."""

import os
import json
import codecs
from pathlib import Path
import re
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl, Qt, QSize, QEvent
from PySide6.QtGui import QFont, QTextCursor, QIcon, QShortcut, QKeySequence, QKeyEvent
from PySide6.QtWidgets import (QApplication, QFileSystemModel, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QSplitter, QStackedWidget,
    QTreeView, QVBoxLayout, QWidget, QComboBox, QDialog, QListWidget, QListWidgetItem, QMenu, QSystemTrayIcon)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from .desktop import Window as VoiceWindow, STYLE
from .harness import runtime_path
from .terminal import powershell_arguments
from .workspace_copy import COPY as SHELL_COPY, translate
from .branding import icon_path, configure_windows_identity
from .local_models_ui import LocalModelsPage
from .design import outline_icon
from .code_view import SourceTabs


class LocalPage(QWebEnginePage):
    """Keep the embedded app on its owned loopback origin."""
    def __init__(self, profile, parent):
        super().__init__(profile, parent)
        self.origin = None

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
        self.setWindowTitle("Kotoba Studio · ことば")
        self.setWindowIcon(QIcon(str(icon_path())))
        self.resize(1536, 960)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(STYLE)
        self.backend = QProcess(self)
        self.backend.setProcessChannelMode(QProcess.MergedChannels)
        self.backend.readyReadStandardOutput.connect(self.backend_output)
        self.backend.errorOccurred.connect(lambda _: self.set_health("failed"))
        self.backend.finished.connect(lambda *_: self.set_health("stopped"))
        self.output = ""
        self.url = None
        self.console_process = QProcess(self)
        self.console_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.console_process.setProcessChannelMode(QProcess.MergedChannels)
        self.console_process.readyReadStandardOutput.connect(self.console_output)
        self.build()
        self.voice.locale_changed.connect(self.apply_locale)
        self.voice.draft_handoff.connect(self.handoff_draft)
        self.voice.busy_changed.connect(lambda busy: self.locale_toggle.setEnabled(not busy))
        self.apply_locale(self.voice.locale)
        self.start_backend()

    def build(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        titlebar = QFrame()
        titlebar.setObjectName("titlebar")
        top = QHBoxLayout(titlebar)
        top.setContentsMargins(16, 8, 14, 8)
        logo = QLabel()
        logo.setPixmap(self.windowIcon().pixmap(26, 26))
        top.addWidget(logo)
        title = QLabel("Kotoba Studio")
        title.setStyleSheet("font-weight:600;font-size:15px;color:#e8e8ec")
        top.addWidget(title)
        top.addSpacing(28)
        self.command_center = QPushButton()
        self.command_center.setObjectName("command-center")
        self.command_center.setMaximumWidth(360)
        self.command_center.setMinimumWidth(220)
        self.command_center.clicked.connect(self.command_palette)
        top.addWidget(self.command_center, 1)
        top.addStretch()
        self.voice_toggle = QPushButton()
        self.voice_toggle.clicked.connect(lambda: self.show_panel(1))
        self.voice_toggle.hide()
        self.locale_toggle = QComboBox()
        self.locale_toggle.setObjectName("interface-language")
        self.locale_toggle.setAccessibleName("Interface language / 表示言語")
        self.locale_toggle.addItem("English", "en")
        self.locale_toggle.addItem("日本語", "ja")
        self.locale_toggle.currentIndexChanged.connect(self.change_locale)
        outer.addWidget(titlebar)
        main = QHBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        side = top
        self.stack = QStackedWidget()
        self.web = QWebEngineView()
        self.browser_profile = QWebEngineProfile("KotobaHarness", self.web)
        self.browser_profile.setPersistentStoragePath(str(self.voice.home / "browser"))
        self.browser_profile.setCachePath(str(self.voice.home / "browser-cache"))
        self.web.setPage(LocalPage(self.browser_profile, self.web))
        self.web.setStyleSheet("background:#191a1e")
        self.stack.addWidget(self.web)
        self.stack.addWidget(QWidget())  # Legacy voice navigation index; voice now lives in the dock.
        self.stack.addWidget(self.files_page())
        self.stack.addWidget(QWidget())
        self.terminal_dock = self.terminal_page()
        self.stack.addWidget(self.routing_page())
        self.stack.addWidget(self.plugins_page())
        self.local_models = LocalModelsPage(self)
        self.stack.addWidget(self.local_models)
        self.nav_keys = ["◈  Workspace / 会話", "◉  Voice / 音声", "⌘  Code / コード", "›_  Terminal", "⇄  Routing / 接続", "⊞  Plugins", "▣  Local models"]
        self.nav = []
        for index, icon in enumerate(("chat", "mic", "code", "terminal", "routing", "plugins", "models")):
            button = QPushButton()
            button.setIcon(outline_icon(icon))
            button.setIconSize(QSize(17, 17))
            button.setObjectName("activity")
            button.setMinimumSize(86, 34)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.show_panel(i))
            if index < 4:
                side.addWidget(button)
            else:
                button.setParent(titlebar)
                button.hide()
            self.nav.append(button)
        self.workspace_menu = QMenu(self)
        self.workspace_actions = []
        for index in (4, 5, 6):
            action = self.workspace_menu.addAction(outline_icon(("routing", "plugins", "models")[index - 4]), "")
            action.triggered.connect(lambda checked=False, i=index: self.show_panel(i))
            self.workspace_actions.append(action)
        self.more_button = QPushButton("···")
        self.more_button.setObjectName("ghost")
        self.more_button.setFixedSize(38, 34)
        self.more_button.setMenu(self.workspace_menu)
        side.addWidget(self.more_button)
        folder = QPushButton()
        folder.setIcon(outline_icon("folder"))
        folder.setIconSize(QSize(18, 18))
        folder.setObjectName("ghost")
        folder.setFixedSize(38, 34)
        folder.setToolTip("Open folder / フォルダーを開く")
        folder.clicked.connect(self.choose_workspace)
        side.addWidget(folder)
        side.addWidget(self.locale_toggle)
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
        self.voice.setVisible(self.voice.preferences.value("ui/voice_dock", True, type=bool))
        main.addWidget(self.workbench, 1)
        outer.addLayout(main, 1)
        statusbar = QFrame()
        statusbar.setObjectName("statusbar")
        status = QHBoxLayout(statusbar)
        status.setContentsMargins(14, 5, 16, 5)
        self.health_key = "starting"
        self.health = QLabel()
        self.health.setStyleSheet("color:#a4b7ad;font-size:11px")
        status.addWidget(self.health)
        status.addStretch()
        self.locale_scope = QLabel()
        self.locale_scope.setStyleSheet("color:#999daa;font-size:11px")
        status.addWidget(self.locale_scope)
        status.addSpacing(18)
        status.addWidget(QLabel("Kotoba Studio  0.5.1"))
        outer.addWidget(statusbar)
        self.setCentralWidget(root)
        self.stack.currentChanged.connect(self.selected_panel)
        for sequence, callback in (("Ctrl+K", self.command_palette), ("Ctrl+Shift+V", lambda: self.show_panel(1)),
                                   ("Ctrl+J", lambda: self.show_panel(3)), ("Ctrl+Shift+E", lambda: self.show_panel(2)),
                                   ("Ctrl+Shift+Space", self.record_shortcut), ("Ctrl+F", self.find_in_file)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
        self.selected_panel(0)

    def record_shortcut(self):
        if self.voice.record_button.isEnabled():
            self.voice.show()
            self.voice.record_button.click()
            self.selected_panel(self.stack.currentIndex())

    def show_panel(self, index):
        if index == 1:
            self.voice.setVisible(self.voice.isHidden())
            self.voice.preferences.setValue("ui/voice_dock", not self.voice.isHidden())
            if not self.voice.isHidden():
                self.workbench.setSizes([max(500, self.width() - 490), 420])
        elif index == 3:
            self.terminal_dock.setVisible(self.terminal_dock.isHidden())
            if not self.terminal_dock.isHidden():
                self.editor_area.setSizes([max(300, self.height() - 330), 230])
                self.command.setFocus()
        else:
            self.stack.setCurrentIndex(index)
        self.selected_panel(self.stack.currentIndex())

    def selected_panel(self, index):
        for i, button in enumerate(self.nav):
            button.setChecked(not self.voice.isHidden() if i == 1 else not self.terminal_dock.isHidden() if i == 3 else i == index)

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
                self.show_panel(item.data(Qt.UserRole))
                dialog.accept()
        query.textChanged.connect(filter_actions)
        query.returnPressed.connect(lambda: activate(actions.currentItem()))
        actions.itemActivated.connect(activate)
        query.setFocus()
        dialog.exec()

    def change_locale(self):
        self.voice.set_locale(self.locale_toggle.currentData())
        self.apply_locale(self.voice.locale)

    def sync_chat_locale(self, locale):
        script = QWebEngineScript()
        script.setName("kotoba-language")
        script.setInjectionPoint(QWebEngineScript.DocumentReady)
        script.setWorldId(QWebEngineScript.MainWorld)
        script.setRunsOnSubFrames(False)
        source = "document.documentElement.dataset.kotobaLocale=" + json.dumps(locale) + ";document.dispatchEvent(new Event('kotoba:locale'));"
        script.setSourceCode(source)
        scripts = self.web.page().scripts()
        for previous in scripts.find("kotoba-language"):
            scripts.remove(previous)
        scripts.insert(script)
        self.web.page().runJavaScript(source)

    def apply_locale(self, locale):
        """Update shell labels without rebuilding web, terminal, or file state."""
        self.locale_toggle.blockSignals(True)
        self.locale_toggle.setCurrentIndex(self.locale_toggle.findData(locale))
        self.locale_toggle.blockSignals(False)
        self.locale_scope.setText(translate("scope", locale))
        self.local_models.set_locale(locale)
        self.source_tabs.set_locale(locale)
        self.update_tray_locale()
        self.command_center.setText("⌕   Search commands…     Ctrl K" if locale == "en" else "⌕   コマンドを検索…     Ctrl K")
        self.voice_toggle.setText("◉ Voice studio" if locale == "en" else "◉ 音声スタジオ")
        for button, key in zip(self.nav, self.nav_keys):
            button.setToolTip(translate(key, locale))
            button.setAccessibleName(translate(key, locale))
        names = ("Chat", "Voice", "Code", "Terminal", "Routing", "Plugins", "Local AI") if locale == "en" else ("会話", "音声", "コード", "ターミナル", "接続", "プラグイン", "ローカル AI")
        for button, name in zip(self.nav, names):
            button.setText(name)
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
        if self.health_key:
            self.set_health(self.health_key)

    def set_health(self, key):
        self.health_key = key
        self.health.setText(translate(key, self.voice.locale))

    def handoff_draft(self, text):
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
            self.source_tabs.query.setFocus()
            self.source_tabs.query.selectAll()
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
        widget, layout = self.panel("Code explorer / コード", "Read files in your selected workspace. Agent edits and diffs remain available in the full Kotoba Studio workspace.")
        self.path_label = QLabel(self.voice.workspace)
        layout.addWidget(self.path_label)
        splitter = QSplitter()
        self.files = QFileSystemModel(self)
        self.files.setReadOnly(True)
        self.files.setRootPath(self.voice.workspace)
        self.tree = QTreeView()
        self.tree.setModel(self.files)
        self.tree.setRootIndex(self.files.index(self.voice.workspace))
        for column in (1, 2, 3):
            self.tree.hideColumn(column)
        self.tree.setMinimumWidth(180)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.clicked.connect(self.view_file)
        self.source_tabs = SourceTabs()
        splitter.addWidget(self.tree)
        splitter.addWidget(self.source_tabs)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)
        return widget

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
            self.path_label.setText(str(path))
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
        widget, layout = self.panel("Model routing / モデル接続", "The full Kotoba Studio Models settings manage provider routes, credentials, endpoints, model discovery, and per-session selection.")
        for title, text in [
            ("01   Add a provider", "Open Workspace → Settings → Models. Add DeepSeek or another supported provider, or configure a compatible gateway with its endpoint and model ID."),
            ("02   Connect credentials", "Store each API key through Kotoba Studio's credential manager. Keep separate keys per provider. This app does not put credentials into source or session exports."),
            ("03   Choose the route", "Choose a provider/model in the chat composer. Voice can use DeepSeek or Kotoba Local. Open Local models to load a GGUF file or connect Ollama / LM Studio."),
        ]:
            frame = QFrame()
            frame.setObjectName("metric")
            box = QVBoxLayout(frame)
            box.addWidget(QLabel(title))
            description = QLabel(text)
            description.setWordWrap(True)
            description.setStyleSheet("color:#a5a8b5;padding:8px")
            box.addWidget(description)
            layout.addWidget(frame)
        open_workspace = QPushButton("Open full Kotoba Studio settings  →")
        open_workspace.clicked.connect(lambda: self.open_settings("models"))
        layout.addWidget(open_workspace)
        voice_settings = QPushButton("Voice-direct API settings / 音声API設定")
        voice_settings.clicked.connect(self.voice.settings)
        layout.addWidget(voice_settings)
        layout.addStretch()
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
            self.voice.workspace = path
            self.files.setRootPath(path)
            self.tree.setRootIndex(self.files.index(path))
            self.path_label.setText(path)
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
        args = ["web", "--no-open", "--host", "127.0.0.1", "--port", "0"]
        if runtime.suffix == ".js":
            self.backend.start("node", [str(runtime), *args])
        else:
            self.backend.start(str(runtime), args)
        QTimer.singleShot(60000, self.startup_deadline)

    def startup_deadline(self):
        if self.url is None and self.backend.state() != QProcess.NotRunning:
            self.set_health("timeout")
            self.backend.kill()

    def backend_output(self):
        self.output = (self.output + bytes(self.backend.readAllStandardOutput()).decode("utf-8", errors="replace"))[-16000:]
        match = re.search(r"http://127\.0\.0\.1:\d+(?:/\?token=[A-Za-z0-9_-]+)?", self.output)
        if match and self.url is None:
            self.url = QUrl(match.group())
            self.web.page().origin = self.url
            self.web.load(self.url)
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
        if self.tray is not None:
            self.tray.hide()
        self.voice.close()
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
                    evidence[locale] = value["lang"]
                    window.grab().save(str(screenshot.with_name(screenshot.stem + "-" + locale + ".png")))
                    switch_next()
                QTimer.singleShot(1000, lambda: window.web.page().runJavaScript(
                    "JSON.stringify({lang:document.documentElement.lang,notice:!![...document.querySelectorAll('[role=dialog]')].find(x=>/Internal Testing Notice|内测声明/.test(x.textContent))})", inspected))
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
