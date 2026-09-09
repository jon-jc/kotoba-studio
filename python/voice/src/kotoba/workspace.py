"""Desktop container for the complete upstream Harness web application."""

import os
import json
import codecs
from pathlib import Path
import re
import sys

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl, Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (QApplication, QFileSystemModel, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton, QSplitter, QStackedWidget,
    QTreeView, QVBoxLayout, QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from .desktop import Window as VoiceWindow, STYLE
from .harness import runtime_path
from .terminal import powershell_arguments


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
        self.voice = VoiceWindow()
        self.setWindowTitle("Kotoba Studio · ことば — DeepSeek Harness")
        self.resize(1536, 960)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(STYLE)
        self.backend = QProcess(self)
        self.backend.setProcessChannelMode(QProcess.MergedChannels)
        self.backend.readyReadStandardOutput.connect(self.backend_output)
        self.backend.errorOccurred.connect(lambda _: self.health.setText("Runtime failed to start · ランタイム起動失敗"))
        self.backend.finished.connect(lambda *_: self.health.setText("Runtime stopped · 停止"))
        self.output = ""
        self.url = None
        self.console_process = QProcess(self)
        self.console_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.console_process.setProcessChannelMode(QProcess.MergedChannels)
        self.console_process.readyReadStandardOutput.connect(self.console_output)
        self.build()
        self.start_backend()

    def build(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QFrame()
        rail.setObjectName("sidebar")
        rail.setFixedWidth(216)
        side = QVBoxLayout(rail)
        side.setContentsMargins(18, 26, 18, 24)
        side.setSpacing(14)
        brand = QLabel("ことば\nKOTOBA STUDIO")
        brand.setStyleSheet("font-size:20px;font-weight:700;color:#d0eddb")
        side.addWidget(brand)
        subtitle = QLabel("Voice × intelligence\n日本語 / English")
        subtitle.setStyleSheet("color:#8ea79b;font-size:12px")
        side.addWidget(subtitle)
        side.addSpacing(28)
        self.stack = QStackedWidget()
        self.web = QWebEngineView()
        self.browser_profile = QWebEngineProfile("KotobaHarness", self.web)
        self.browser_profile.setPersistentStoragePath(str(self.voice.home / "browser"))
        self.browser_profile.setCachePath(str(self.voice.home / "browser-cache"))
        self.web.setPage(LocalPage(self.browser_profile, self.web))
        self.web.setStyleSheet("background:#101416")
        self.stack.addWidget(self.web)
        self.stack.addWidget(self.voice)
        self.stack.addWidget(self.files_page())
        self.stack.addWidget(self.terminal_page())
        self.stack.addWidget(self.routing_page())
        self.stack.addWidget(self.plugins_page())
        labels = ["◈  Workspace / 会話", "◉  Voice / 音声", "⌘  Code / コード", "›_  Terminal", "⇄  Routing / 接続", "⊞  Plugins"]
        self.nav = []
        for index, label in enumerate(labels):
            button = QPushButton(label)
            button.setStyleSheet("text-align:left;padding:13px 9px;font-size:12px")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setChecked(index == 0)
            button.clicked.connect(lambda checked=False, i=index: self.stack.setCurrentIndex(i))
            side.addWidget(button)
            self.nav.append(button)
        side.addStretch()
        folder = QPushButton("Open workspace…\n作業フォルダー")
        folder.clicked.connect(self.choose_workspace)
        side.addWidget(folder)
        self.health = QLabel("Starting Harness…\n起動中")
        self.health.setWordWrap(True)
        self.health.setStyleSheet("color:#9fb8aa;font-size:11px")
        side.addWidget(self.health)
        footer = QLabel("DEEPSEEK HARNESS\n+ OPENWHISPR\n\nLocal voice · Full runtime")
        footer.setStyleSheet("font-size:10px;color:#738f7d")
        side.addWidget(footer)
        layout.addWidget(rail)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.stack.currentChanged.connect(lambda index: self.nav[index].setChecked(True))

    def panel(self, title, description):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 32, 32, 28)
        header = QLabel(title)
        header.setStyleSheet("font-size:28px;font-weight:600")
        layout.addWidget(header)
        label = QLabel(description)
        label.setWordWrap(True)
        label.setStyleSheet("color:#a3b8ad;padding-bottom:18px")
        layout.addWidget(label)
        return widget, layout

    def files_page(self):
        widget, layout = self.panel("Code explorer / コード", "Read files in your selected workspace. Agent edits and diffs remain available in the full Harness workspace.")
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
        self.tree.setMinimumWidth(240)
        self.tree.clicked.connect(self.view_file)
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        self.code.setFont(QFont("Consolas", 12))
        self.code.setPlaceholderText("Select a source file · ファイルを選択")
        splitter.addWidget(self.tree)
        splitter.addWidget(self.code)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter, 1)
        return widget

    def view_file(self, index):
        path = Path(self.files.filePath(index))
        if not path.is_file():
            return
        try:
            if path.stat().st_size > 1024 * 1024:
                self.code.setPlainText("Preview limited to 1 MiB. Open larger files in your editor.")
                return
            content = path.read_text(encoding="utf-8")
            if "\x00" in content:
                raise UnicodeError("Binary file")
            self.code.setPlainText(content)
            self.path_label.setText(str(path))
        except (OSError, UnicodeError):
            self.code.setPlainText("This file cannot be displayed as UTF-8 text.")

    def terminal_page(self):
        widget, layout = self.panel("Terminal / ターミナル", "Local PowerShell command console. For interactive PTY sessions, use the terminal tools in the Harness workspace.")
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
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
                self.console.appendPlainText("PowerShell could not start.")
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
        widget, layout = self.panel("Model routing / モデル接続", "The full Harness Models settings manage provider routes, credentials, endpoints, model discovery, and per-session selection.")
        for title, text in [
            ("01   Add a provider", "Open Workspace → Settings → Models. Add DeepSeek or another supported provider, or configure a compatible gateway with its endpoint and model ID."),
            ("02   Connect credentials", "Store each API key through Harness's credential manager. Keep separate keys per provider. This app does not put credentials into source or session exports."),
            ("03   Choose the route", "Choose a provider/model in the chat composer. Voice-direct SDK settings currently select the official DeepSeek route; reviewed voice text can also be copied into any Harness chat."),
        ]:
            frame = QFrame()
            frame.setObjectName("metric")
            box = QVBoxLayout(frame)
            box.addWidget(QLabel(title))
            description = QLabel(text)
            description.setWordWrap(True)
            description.setStyleSheet("color:#a4b7ac;padding:8px")
            box.addWidget(description)
            layout.addWidget(frame)
        open_workspace = QPushButton("Open full Harness settings  →")
        open_workspace.clicked.connect(lambda: self.open_settings("models"))
        layout.addWidget(open_workspace)
        voice_settings = QPushButton("Voice-direct API settings / 音声API設定")
        voice_settings.clicked.connect(self.voice.settings)
        layout.addWidget(voice_settings)
        layout.addStretch()
        return widget

    def plugins_page(self):
        widget, layout = self.panel("Plugin workspace / プラグイン", "The original Cordis plugin architecture remains intact. Inspect active plugins and model adapters in Harness Settings → Plugins.")
        description = QLabel("Tools · Agent presets · Model adapters · Skills · Subagents · Workflows\n\nUse the upstream plugin interface to inspect the complete composition. External plugin installation follows the dsh profile workflow and requires pnpm. Plugins execute code with the runtime's access; inspect their source before installing.")
        description.setWordWrap(True)
        layout.addWidget(description)
        button = QPushButton("Open full Harness workspace  →")
        button.clicked.connect(lambda: self.open_settings("plugins"))
        layout.addWidget(button)
        layout.addStretch()
        return widget

    def open_settings(self, section):
        """Navigate existing upstream controls; credentials stay in their owning UI."""
        self.stack.setCurrentIndex(0)
        labels = {"models": ["Models", "模型"], "plugins": ["Plugins", "插件"]}[section]
        script = """(() => {
            const buttons = () => Array.from(document.querySelectorAll('button'));
            const find = labels => buttons().find(b => labels.includes(b.textContent.trim()));
            const trigger = find(['Settings', '设置']);
            if (!trigger || trigger.closest('[inert]')) return false;
            if (trigger.getAttribute('aria-expanded') !== 'true') trigger.click();
            return true;
        })()"""
        def opened(ok):
            if ok:
                QTimer.singleShot(200, lambda: self.web.page().runJavaScript(
                    "Array.from(document.querySelectorAll('button')).find(b => " + json.dumps(labels) + ".includes(b.textContent.trim()))?.click()"))
            else:
                self.health.setText("Complete Harness setup first.\n初期設定を完了してください。")
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
            self.health.setText("Startup timed out. Inspect local Harness configuration.")
            self.backend.kill()

    def backend_output(self):
        self.output = (self.output + bytes(self.backend.readAllStandardOutput()).decode("utf-8", errors="replace"))[-16000:]
        match = re.search(r"http://127\.0\.0\.1:\d+(?:/\?token=[A-Za-z0-9_-]+)?", self.output)
        if match and self.url is None:
            self.url = QUrl(match.group())
            self.web.page().origin = self.url
            self.web.load(self.url)
            self.health.setText("● Runtime connected\nローカル接続")

    def closeEvent(self, event):
        if self.voice.job is not None or self.voice.stream is not None:
            self.stack.setCurrentIndex(1)
            self.voice.status.setText(self.voice.t("busy_close"))
            event.ignore()
            return
        self.voice.close()
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
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kotoba")
    app.setOrganizationName("Kotoba")
    window = Workspace()
    window.show()
    if "--smoke" in sys.argv:
        completed = False
        def check():
            if not completed:
                window.web.page().runJavaScript("JSON.stringify({buttons:document.querySelectorAll('button').length, batches:window.__DSH_BOOT__?.batches?.length || 0, failed:document.body.innerText.includes('Failed to load plugins')})", result)
        def result(raw):
            nonlocal completed
            if completed or not raw:
                return
            state = json.loads(raw)
            if state["buttons"] < 1 or state["batches"] < 1 or state["failed"]:
                return
            completed = True
            screenshot = Path(os.environ.get("KOTOBA_SCREENSHOT", "kotoba-workspace.png"))
            window.grab().save(str(screenshot))
            screenshot.with_suffix(".json").write_text(json.dumps({"runtime_ready": True, **state}), encoding="utf-8")
            window.close()
        timer = QTimer(window)
        timer.timeout.connect(check)
        timer.start(1000)
        def deadline():
            if not completed:
                window.close()
                app.exit(1)
        QTimer.singleShot(70000, deadline)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
