"""Native bilingual access settings with explicit scope and full-access acknowledgment."""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QComboBox, QRadioButton,
                              QButtonGroup, QCheckBox, QPushButton, QDialogButtonBox)
from .access import AccessSettings, MODES
from .desktop import Job

COPY = {
    "en": [
        ("Read-only", "Inspect files. Changes need a separately approved escalation or a different access level."),
        ("Workspace access · Recommended", "Edit project files and run commands within workspace write limits. Broader execution requires approval."),
        ("Full access", "Agent tools can modify files outside the workspace and run unrestricted commands under your Windows account."),
    ],
    "ja": [
        ("読み取り専用", "ファイルを確認できます。変更には個別の承認またはアクセスレベルの変更が必要です。"),
        ("ワークスペース内の変更 · 推奨", "作業フォルダー内の編集とコマンド実行を許可します。制限を超える実行には承認が必要です。"),
        ("フルアクセス", "作業フォルダー外のファイル変更や、Windows アカウントの権限内で制限のないコマンド実行を許可します。"),
    ],
}


class AccessDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.job = None
        self.view = None
        self.current = None
        self.service = AccessSettings(owner.url.toString())
        self.setWindowTitle(self.tr("Computer access", "コンピューターへのアクセス"))
        self.setMinimumWidth(570)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        heading = QLabel(self.tr("Choose what your agents can change", "エージェントに許可する操作を選択"))
        heading.setStyleSheet("font-size:20px;font-weight:600")
        layout.addWidget(heading)
        self.scope = QComboBox()
        self.scope.setAccessibleName(self.tr("Apply to", "適用先"))
        layout.addWidget(self.scope)
        self.group = QButtonGroup(self)
        self.choices = []
        for index, (title, detail) in enumerate(COPY[owner.voice.locale]):
            button = QRadioButton(title)
            button.setStyleSheet("font-weight:600;padding-top:7px")
            button.setProperty("mode", MODES[index])
            self.group.addButton(button, index)
            button.toggled.connect(self.selection_changed)
            self.choices.append(button)
            layout.addWidget(button)
            label = QLabel(detail)
            label.setWordWrap(True)
            layout.addWidget(label)
        self.ack = QCheckBox(self.tr("I allow this agent to change files outside the workspace.", "作業フォルダー外のファイル変更を許可します。"))
        self.ack.toggled.connect(self.selection_changed)
        layout.addWidget(self.ack)
        details = QLabel(self.tr(
            "These settings govern agent tools, not commands you type yourself or desktop permissions granted to plugins. Windows restrictions primarily limit writes; reads and network traffic are not fully isolated. Chat shows one-time approval requests. The voice SDK denies requests it cannot approve; use Add to chat for interactive approvals. Existing conversations keep their own level until selected above.",
            "この設定はエージェントのツールに適用されます。手入力のコマンドやプラグインの権限は対象外です。Windows では主に書き込みを制限し、読み取り・ネットワークは完全には隔離しません。個別の承認はチャットに表示されます。音声 SDK は承認できない要求を拒否するため、対話的な承認には「チャットに追加」を使用してください。既存の会話は上で選択するまで設定を維持します。"))
        details.setWordWrap(True)
        details.setStyleSheet("color:#a4a7b0;font-size:11px")
        layout.addWidget(details)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText(self.tr("Close", "閉じる"))
        self.apply_button = QPushButton(self.tr("Apply access level", "アクセス設定を適用"))
        buttons.addButton(self.apply_button, QDialogButtonBox.ActionRole)
        self.apply_button.clicked.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.scope.currentIndexChanged.connect(self.load_scope)
        self.work(self.service.describe, self.loaded)

    def tr(self, en, ja):
        return en if self.owner.voice.locale == "en" else ja

    def work(self, task, result):
        if self.job is not None:
            return
        self.scope.setEnabled(False)
        for button in self.choices:
            button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.status.setText(self.tr("Updating access settings…", "アクセス設定を更新中…"))
        self.job = Job(lambda emit: task())
        self.job.result.connect(result)
        self.job.failure.connect(self.status.setText)
        self.job.finished.connect(self.settled)
        self.job.start()

    def settled(self):
        job, self.job = self.job, None
        job.deleteLater()
        self.scope.setEnabled(self.view is not None)
        for button in self.choices:
            button.setEnabled(self.current is not None)
        self.selection_changed()

    def loaded(self, view):
        self.view = view
        self.scope.blockSignals(True)
        self.scope.clear()
        self.scope.addItem(self.tr("Default for new chats + next voice conversation", "新しいチャット・次の音声会話の既定値"), None)
        for session in view["sessions"]:
            title = session.get("projections", {}).get("values", {}).get("title", {}).get("title") or session["sessionId"]
            self.scope.addItem(str(title), session["sessionId"])
        self.scope.blockSignals(False)
        self.show_mode(view["mode"])

    def show_mode(self, mode):
        self.current = mode
        self.ack.setChecked(False)
        self.group.setExclusive(False)
        for button in self.choices:
            button.setChecked(button.property("mode") == mode)
        self.group.setExclusive(True)
        label = COPY[self.owner.voice.locale][MODES.index(mode)][0] if mode in MODES else self.tr("Custom", "カスタム")
        self.status.setText(self.tr("Current: ", "現在の設定: ") + label)

    def load_scope(self):
        self.current = None
        session = self.scope.currentData()
        if session:
            self.work(lambda: self.service.session_mode(session), self.show_mode)
        elif self.view:
            self.show_mode(self.view["mode"])
            for button in self.choices:
                button.setEnabled(True)
            self.selection_changed()

    def selection_changed(self, *_):
        button = self.group.checkedButton()
        selected = button.property("mode") if button else None
        needs_ack = selected == "danger-full-access" and selected != self.current
        self.ack.setVisible(needs_ack)
        self.apply_button.setEnabled(self.job is None and self.current is not None and selected is not None
                                     and selected != self.current and (not needs_ack or self.ack.isChecked()))

    def save(self):
        mode = self.group.checkedButton().property("mode")
        if mode == "danger-full-access" and not self.ack.isChecked():
            return
        session = self.scope.currentData()
        if session:
            self.work(lambda: self.service.session_mode(session, mode), self.show_mode)
        else:
            revision = self.view["revision"]
            def saved(view):
                self.owner.voice.harness.close()
                self.loaded(view)
            self.work(lambda: self.service.set_default(mode, revision), saved)

    def reject(self):
        if self.job is None:
            super().reject()
