"""One agent workspace with Kotoba's voice, API chat and collaboration tools."""

import json
from pathlib import Path
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QStackedWidget
from .fleet_runtime import FleetRuntime


class FleetWorkspace(QWidget):
    tool_requested = Signal(str)
    context_changed = Signal(str)

    def __init__(self, home, parent=None):
        super().__init__(parent)
        self.locale = "en"
        self.current_path = ""
        self.pending = False
        self.runtime = FleetRuntime(home, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(16, 0, 16, 0)
        self.context = QLabel()
        self.context.setTextFormat(Qt.PlainText)
        self.context.setStyleSheet("color:#d3c49e;font-size:12px;padding:10px 0;")
        bar.addWidget(self.context, 1)
        self.context.hide()
        self.buttons = {}
        for key in ("accounts", "api", "voice", "handoff", "messaging"):
            button = QPushButton(self)
            button.setObjectName("ghost")
            button.clicked.connect(lambda checked=False, tool=key: self.tool_requested.emit(tool))
            self.buttons[key] = button
            button.hide()  # Actions live in the unified desktop rail.
        layout.addLayout(bar)
        self.pages = QStackedWidget()
        waiting = QWidget()
        waiting_layout = QVBoxLayout(waiting)
        waiting_layout.setContentsMargins(90, 70, 90, 70)
        waiting_layout.addStretch()
        self.title = QLabel()
        self.title.setStyleSheet("font-size:30px;font-weight:600;color:#e8eee9;")
        waiting_layout.addWidget(self.title)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setStyleSheet("font-size:15px;color:#a4aaa7;padding:12px 0;")
        waiting_layout.addWidget(self.description)
        self.status = QLabel()
        self.status.setWordWrap(True)
        waiting_layout.addWidget(self.status)
        self.retry = QPushButton()
        self.retry.setMaximumWidth(240)
        self.retry.clicked.connect(self.runtime.start)
        waiting_layout.addWidget(self.retry)
        waiting_layout.addStretch()
        self.pages.addWidget(waiting)
        self.foreign_window = None
        self.container = None
        layout.addWidget(self.pages, 1)
        self.runtime.ready.connect(self.connect_runtime)
        self.runtime.state.connect(self.set_state)
        self.timer = QTimer(self)
        self.timer.setInterval(1200)
        self.timer.timeout.connect(self.poll)
        self.state = "stopped"
        self.set_locale("en")

    def tr(self, en, ja):
        return ja if self.locale == "ja" else en

    def set_locale(self, locale):
        self.locale = locale
        self.title.setText(self.tr("Your words. Your agents. Your workspace.", "ことばから、エージェントとつくる。"))
        self.description.setText(self.tr("Speak or type in English or Japanese. Build with your coding agents, review their work, and turn meeting notes into your team's next steps—all in Kotoba Studio.", "日本語でも、英語でも。声やテキストでエージェントと開発し、変更をレビュー。会議のメモをチームの次の一歩へ。Kotoba Studio で、ひとつにつながるワークフロー。"))
        self.retry.setText(self.tr("Open workspace", "ワークスペースを開く"))
        for key, (en, ja) in {"accounts": ("Agent accounts", "エージェントのアカウント"), "api": ("API chat", "API チャット"), "voice": ("Dictate", "音声入力"), "handoff": ("Team handoff", "引き継ぎ"), "messaging": ("Messages", "メッセージ")}.items():
            self.buttons[key].setText(self.tr(en, ja))
        self.set_state(self.state)
        self.poll()

    def set_state(self, state):
        self.state = state
        messages = {
            "starting": ("Preparing your agent workspace…", "エージェントのワークスペースを準備しています…"),
            "ready": ("Workspace connected", "ワークスペースに接続しました"),
            "failed": ("The agent runtime stopped. Reopen to reconnect; saved worktrees are preserved.", "実行環境が停止しました。再接続してください。保存済みの作業ツリーは保持されています。"),
            "missing": ("The agent runtime is not included in this build. Install the complete Kotoba Studio build.", "このビルドにはエージェント実行環境が含まれていません。完全版の Kotoba Studio をインストールしてください。"),
            "timeout": ("Startup took too long. Reopen the workspace to retry.", "起動に時間がかかりすぎました。再度開いてください。"),
            "stopped": ("Use each agent’s own sign-in and subscription. Provider access and limits still apply.", "各エージェントのログインとサブスクリプションを使用します。利用条件と上限は提供元に従います。"),
        }
        self.status.setText(self.tr(*messages[state]))
        self.retry.setEnabled(state != "starting")
        self.buttons["accounts"].setEnabled(state == "ready")
        if state != "ready":
            self.timer.stop()
            self.current_path = ""
            self.pages.setCurrentIndex(0)
            self.context.setText(self.tr("Kotoba Studio · Agent workspace", "Kotoba Studio · エージェント"))

    def connect_runtime(self, handle):
        if self.container is not None:
            self.pages.removeWidget(self.container)
            self.container.deleteLater()
        self.foreign_window = QWindow.fromWinId(int(handle))
        self.container = QWidget.createWindowContainer(self.foreign_window, self)
        self.container.setAttribute(Qt.WA_NativeWindow)
        self.container.setFocusPolicy(Qt.StrongFocus)
        self.pages.addWidget(self.container)
        self.pages.setCurrentWidget(self.container)
        QTimer.singleShot(0, self.present)
        self.timer.start()
        self.poll()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.present)

    def hideEvent(self, event):
        if self.container is not None and self.runtime.address:
            self.runtime.request("present", "hidden")
        super().hideEvent(event)

    def present(self):
        if self.container is not None and self.isVisible() and self.runtime.address:
            self.runtime.request("present", "", self.present_result)

    def present_result(self, accepted):
        if accepted is True and self.container is not None and self.foreign_window is not None:
            # Electron restores its former top-level screen position on show.
            # Our native container owns the child coordinates, including on restore.
            self.foreign_window.setGeometry(self.container.rect().adjusted(0, 0, 1, 0))
            QTimer.singleShot(0, self.fit_surface)
        elif accepted is not True:
            self.context.show()
            self.context.setText(self.tr("Could not display the agent workspace. Switch to API chat or reopen Agents to retry.", "エージェント画面を表示できませんでした。API チャットに切り替えるか、エージェント画面を開き直してください。"))

    def fit_surface(self):
        if self.container is not None and self.foreign_window is not None:
            self.foreign_window.setGeometry(self.container.rect())

    def navigate(self, target):
        self.runtime.request("navigate", target, self.navigation_result)

    def navigation_result(self, accepted):
        if accepted is not True:
            self.context.show()
            self.context.setText(self.tr("Could not open this agent page. Reopen Agents and try again.", "エージェントのページを開けませんでした。エージェント画面を開き直して再試行してください。"))

    def poll(self):
        if not self.runtime.address or self.pending:
            return
        self.pending = True
        self.runtime.request("snapshot", self.locale, self.snapshot)

    def snapshot(self, value):
        self.pending = False
        try:
            state = json.loads(value) if isinstance(value, str) else value
        except ValueError:
            return
        if not isinstance(state, dict):
            return
        path = state.get("path", "")
        self.context.setText(str(state.get("title") or self.tr("Choose a project to start", "プロジェクトを選んで開始"))[:180])
        if state.get("local") is not True:
            self.current_path = ""
            if path:
                self.context.show()
                self.context.setText(self.context.text() + self.tr(" · Remote task; local tools keep their own folder", " · リモートタスク：ローカルツールは個別のフォルダーを使用"))
        # Remote worktrees stay owned by their runtime and never become local file paths.
        if isinstance(path, str) and path != self.current_path and state.get("local") is True and Path(path).is_absolute() and Path(path).is_dir():
            self.current_path = path
            self.context_changed.emit(path)

    def add_project(self, path):
        self.runtime.request("addProject", str(path), self.project_result)

    def project_result(self, accepted):
        if accepted is not True:
            self.context.show()
            self.context.setText(self.tr("Could not add this project. Open a Git repository or create a workspace in Agents.", "プロジェクトを追加できませんでした。Git リポジトリを開くか、エージェント画面でワークスペースを作成してください。"))

    def draft(self, text):
        self.runtime.request("draft", text, self.draft_result)

    def draft_result(self, accepted):
        if accepted is not True:
            self.context.show()
            self.context.setText(self.tr("Select an agent chat before inserting voice text. Your text remains in Voice.", "音声テキストを挿入する前にエージェントのチャットを選択してください。テキストは音声画面に保持されています。"))

    def shutdown(self):
        self.timer.stop()
        self.runtime.stop()
