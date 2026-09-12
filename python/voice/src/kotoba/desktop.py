"""Native bilingual desktop voice workspace with an explicit review boundary."""

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot, QStandardPaths, QSettings
from PySide6.QtGui import QFont, QTextCursor, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTextBrowser,
    QVBoxLayout, QWidget, QListWidget, QProgressBar)
from PySide6.QtTextToSpeech import QTextToSpeech

from .harness import HarnessSession
from .speech import SpeechConfig, SpeechEngine, load_audio
from .evaluate import score
from .audio_sources import sources, LoopbackStream
from .dictation import format_dictation
from .snippets import load_snippets, save_snippets, expand_snippets
from .branding import icon_path
from .speech_models import MODEL_CHOICES, resolve_model, ModelDownloadRequired
from .voice_routes import load_routes
from .global_dictation import GlobalDictation
from .meetings import MeetingStore
from .selection_widgets import ClickComboBox as QComboBox, ClickTabWidget as QTabWidget


COPY = {
    "en": {
        "tagline": "Your voice. The full power of Kotoba Studio.", "workspace": "VOICE WORKSPACE",
        "record": "●  Record", "stop": "■  Transcribe", "import": "Import audio", "send": "Send reviewed text  →",
        "draft": "TRANSCRIPT · REVIEW BEFORE SENDING", "placeholder": "Speak in Japanese or English, import a recording, or type here…",
        "conversation": "Conversation", "activity": "Agent activity", "evaluation": "Accuracy lab",
        "ready": "Ready to listen", "recording": "Recording locally · 60 second limit", "working": "Working…",
        "privacy": "Local keeps audio on this device. Cloud uploads audio to your selected endpoint. Reviewed instructions go to your agent provider.",
        "settings": "Settings", "new": "+ New session", "export": "Export session", "speak": "Read reply aloud",
        "welcome": "Speak naturally. Act deliberately.", "intro": "Japanese and English voice input, with tools, code, and agent workflows in one place.\n\n1   Record or import audio\n2   Review names, numbers, and intent\n3   Send your instruction to Kotoba Studio",
        "model": "Speech model", "lang": "Input language", "speed": "INFERENCE", "duration": "AUDIO", "rtf": "REAL-TIME FACTOR",
        "review": "Review required", "clean": "Check names and numbers before sending.", "reference": "Human-checked reference",
        "compare": "Compare with transcript", "no_ref": "Enter a reference and transcript first.",
        "configure": "Prepare your speech model once before recording. English recommends Parakeet; Japanese recommends Kotoba-Whisper. Local transcription then works offline.",
        "key": "API key (this session only)", "llm": "Kotoba Studio model", "folder": "Agent workspace", "browse": "Choose folder",
        "glossary": "Names and technical terms (optional)", "device": "Inference device", "save": "Apply", "error": "Action could not complete",
        "busy_close": "Wait for the current operation to finish before closing. No agent request will be replayed automatically.",
        "no_voice": "No installed voice matches the reply language. Install a Japanese/English Windows speech voice.",
        "empty": "No speech detected. Try again closer to the microphone.", "prepared": "Model ready", "prepare": "Download / warm model",
        "result": "Reply", "you": "You", "events": "Events", "no_export": "There is no session data to export yet.",
    },
    "ja": {
        "tagline": "声でつながる、Kotoba Studio のすべての力。", "workspace": "音声ワークスペース",
        "record": "●  録音", "stop": "■  文字起こし", "import": "音声を読み込む", "send": "確認した内容を送信  →",
        "draft": "文字起こし · 送信前に確認", "placeholder": "日本語・英語で話す、音声を読み込む、または入力してください…",
        "conversation": "会話", "activity": "エージェントの動作", "evaluation": "精度ラボ",
        "ready": "録音できます", "recording": "ローカル録音中 · 最大60秒", "working": "処理中…",
        "privacy": "ローカルでは音声を端末内で処理します。クラウドでは選択した提供者へ音声を送信します。確認した指示はエージェントに送信します。",
        "settings": "設定", "new": "+ 新しい会話", "export": "会話をエクスポート", "speak": "返答を読み上げる",
        "welcome": "自然に話して、確かめて実行。", "intro": "日本語と英語の音声入力を、エージェント機能につなげます。\n\n1   録音する、または音声を読み込む\n2   名前・数字・意図を確認する\n3   Kotoba Studio に指示を送信する",
        "model": "音声モデル", "lang": "入力言語", "speed": "処理時間", "duration": "音声の長さ", "rtf": "実時間比",
        "review": "確認が必要です", "clean": "送信前に名前と数字を確認してください。", "reference": "人手で確認した正解文",
        "compare": "文字起こしと比較", "no_ref": "正解文と文字起こしを入力してください。",
        "configure": "録音前にモデルを準備してください。英語は Parakeet、日本語は Kotoba-Whisper が推奨です。準備後はオフラインで文字起こしできます。",
        "key": "APIキー（今回のみ）", "llm": "Kotoba Studio モデル", "folder": "作業フォルダー", "browse": "フォルダーを選ぶ",
        "glossary": "名前・専門用語（任意）", "device": "処理デバイス", "save": "適用", "error": "処理を完了できませんでした",
        "busy_close": "処理の完了後に終了してください。エージェントへの指示は自動で再送されません。",
        "no_voice": "返答の言語に対応する音声がありません。Windowsの日本語・英語音声をインストールしてください。",
        "empty": "音声が検出されませんでした。マイクに近づいて再度お試しください。", "prepared": "モデルを準備しました", "prepare": "モデルを準備",
        "result": "返答", "you": "あなた", "events": "イベント", "no_export": "まだエクスポートするデータがありません。",
    },
}

from .design import STYLE



class Job(QThread):
    result = Signal(object)
    failure = Signal(str)
    activity = Signal(str)

    def __init__(self, task):
        super().__init__()
        self.task = task

    def run(self):
        try:
            self.result.emit(self.task(self.activity.emit))
        except Exception as error:
            self.failure.emit(str(error))


class Window(QMainWindow):
    locale_changed = Signal(str)
    busy_changed = Signal(bool)
    draft_handoff = Signal(str)
    model_progress = Signal(object)

    def __init__(self, embedded=False):
        super().__init__()
        self.embedded = embedded
        self.locale = "ja"
        self.home = Path(os.environ.get("KOTOBA_HOME") or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.home.mkdir(parents=True, exist_ok=True)
        self.preferences = QSettings(str(self.home / "preferences.ini"), QSettings.IniFormat)
        self.locale = self.preferences.value("locale", "ja")
        if self.locale not in COPY:
            self.locale = "ja"
        self.snippets = []
        self.snippet_error = ""
        try:
            self.snippets = load_snippets(self.home / "snippets.json")
        except (OSError, ValueError) as error:
            self.snippet_error = str(error)
        self.engine = SpeechEngine(self.home / "models")
        self.harness = HarnessSession(self.home / "harness")
        self.config = SpeechConfig()
        self.api_key = ""
        self.provider = self.preferences.value("voice/provider", "deepseek-official")
        self.model = self.preferences.value("voice/model", "deepseek-v4-flash")
        self.routes = []
        self.runtime_url = None
        self.after_job = None
        self.workspace = str(self.home / "workspace")
        Path(self.workspace).mkdir(exist_ok=True)
        self.job = None
        self.stream = None
        self.frames = []
        self.record_error = ""
        self.last_transcript = None
        self.last_reply = ""
        self.entries = []
        self.meeting_active = False
        self.meeting_store = MeetingStore(self.home / "meetings.sqlite3")
        self.meeting_store.recover()
        self.global_dictation = GlobalDictation(self)
        self.tts = QTextToSpeech(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.record)
        self.setWindowTitle("Kotoba Studio · ことば")
        self.setWindowIcon(QIcon(str(icon_path())))
        self.resize(1360, 890)
        self.setMinimumSize(360, 560) if embedded else self.setMinimumSize(1080, 740)
        self.setStyleSheet(STYLE)
        self.build()
        self.model_progress.connect(self.show_model_progress)

    def route_controls(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        self.agent_provider = QComboBox()
        self.agent_provider.setAccessibleName("Agent provider / エージェント接続先")
        self.agent_model = QComboBox()
        self.agent_model.setEditable(True)
        self.agent_model.setAccessibleName("Agent model / エージェントモデル")
        self.agent_model.setInsertPolicy(QComboBox.NoInsert)
        self.agent_model.lineEdit().setMaxLength(512)
        row = QHBoxLayout()
        for widget in (self.agent_provider, self.agent_model):
            widget.setMinimumWidth(0)
            widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            widget.setMinimumContentsLength(8)
            row.addWidget(widget, 1)
        layout.addLayout(row)
        self.refresh_routes_button = QPushButton("Refresh models" if self.locale == "en" else "モデル一覧を更新")
        self.refresh_routes_button.setObjectName("ghost")
        self.refresh_routes_button.clicked.connect(self.refresh_routes)
        self.route_hint = QLabel("Configure providers in Chat Settings → Models." if self.locale == "en" else "チャット設定のモデル画面で接続先を追加できます。")
        self.route_hint.setWordWrap(True)
        self.route_hint.setObjectName("micro")
        for widget in (self.refresh_routes_button, self.route_hint):
            layout.addWidget(widget)
        self.agent_provider.currentIndexChanged.connect(self.select_provider)
        self.agent_model.currentTextChanged.connect(self.select_model)
        self.apply_routes(self.routes)
        return box

    def refresh_routes(self):
        if (self.runtime_url and self.job is None and self.stream is None
                and not self.meeting_active and not getattr(self, "permission_dialog_active", False)):
            self.work(lambda emit: load_routes(self.runtime_url), self.apply_routes)

    def apply_routes(self, routes):
        self.routes = routes
        preferred_id = self.provider
        current = next((route for route in routes if route["id"] == self.provider), None)
        if not self.api_key and (current is None or not current["configured"]):
            preferred = next((route for route in routes if route["configured"] and route["models"]), None)
            if preferred is not None:
                preferred_id = preferred["id"]
        self.agent_provider.blockSignals(True)
        self.agent_provider.clear()
        for route in routes:
            self.agent_provider.addItem(route["name"], route["id"])
        self.agent_provider.setCurrentIndex(self.agent_provider.findData(preferred_id))
        self.agent_provider.blockSignals(False)
        if self.agent_provider.currentIndex() >= 0:
            self.select_provider()
        else:
            self.agent_model.blockSignals(True)
            self.agent_model.clear()
            self.agent_model.blockSignals(False)
            self.agent_model.setEnabled(False)
            self.route_label.clear()
            self.route_hint.setText("Choose an available provider to continue." if self.locale == "en" else "利用可能な接続先を選択してください。")

    def select_provider(self, *_):
        selected = self.agent_provider.currentData()
        route = next((r for r in self.routes if r["id"] == selected), None)
        if route is None:
            return
        previous = self.model if selected == self.provider else ""
        if previous and self.preferences.value("voice/model_provider", "") != selected:
            previous = previous if any(m["id"] == previous for m in route["models"]) else ""
        if selected != self.provider:
            self.api_key = ""
        self.provider = selected
        self.agent_model.blockSignals(True)
        self.agent_model.clear()
        for model in route["models"]:
            self.agent_model.addItem(model["id"])
        # Restore an explicit custom model only for its owning provider.
        self.agent_model.setCurrentText(previous or (route["models"][0]["id"] if route["models"] else ""))
        self.agent_model.setEnabled(route["configured"])
        self.route_hint.setText(("Uses your saved provider credentials. Custom model IDs are supported." if self.locale == "en" else "保存済みの認証情報を使用します。モデル ID の直接入力も可能です。") if route["configured"] else ("Set up this provider in Chat Settings → Models, then refresh." if self.locale == "en" else "チャット設定でこの接続先を設定し、一覧を更新してください。"))
        self.agent_model.blockSignals(False)
        self.select_model(self.agent_model.currentText())

    def select_model(self, model):
        self.model = model.strip()
        self.preferences.setValue("voice/provider", self.provider)
        self.preferences.setValue("voice/model", self.model)
        self.preferences.setValue("voice/model_provider", self.provider)
        self.route_label.setText(self.provider + " · " + self.model)

    def setup_language(self):
        chosen = self.preferences.value("speech/language", self.locale)
        self.language.setCurrentIndex(max(0, self.language.findData(chosen)))
        self.language.currentIndexChanged.connect(lambda _: self.preferences.setValue("speech/language", self.language.currentData()))

    def t(self, key):
        return COPY[self.locale][key]

    def button(self, key, callback, name=""):
        button = QPushButton(self.t(key))
        button.setObjectName(name)
        button.clicked.connect(callback)
        return button

    def label(self, text, name=""):
        label = QLabel(text)
        label.setObjectName(name)
        label.setWordWrap(True)
        return label

    def build(self):
        if self.embedded:
            self.build_compact()
            return
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(26)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 24, 22, 24)
        side.setSpacing(18)
        side.addWidget(self.label("ことば  /  Kotoba", "brand"))
        side.addWidget(self.label(self.t("tagline"), "muted"))
        side.addSpacing(20)
        self.new_button = self.button("new", self.new_session)
        side.addWidget(self.new_button)
        side.addWidget(self.label(self.t("lang"), "muted"))
        self.language = QComboBox()
        self.language.addItem("日本語", "ja")
        self.language.addItem("English", "en")
        self.language.addItem("Auto · 日本語 / English", "auto")
        self.setup_language()
        side.addWidget(self.language)
        side.addWidget(self.label(self.t("model"), "muted"))
        self.speech_model = QComboBox()
        self.populate_speech_models()
        side.addWidget(self.speech_model)
        self.prepare_button = self.button("prepare", self.prepare)
        side.addWidget(self.prepare_button)
        side.addWidget(self.workflow_controls())
        side.addWidget(self.label(self.t("configure"), "muted"))
        side.addStretch()
        self.settings_button = self.button("settings", self.settings)
        side.addWidget(self.settings_button)
        side.addWidget(self.button("export", self.export))
        switch = QPushButton("日本語  ⇄  English")
        switch.clicked.connect(self.switch_locale)
        self.locale_button = switch
        side.addWidget(switch)
        switch.setVisible(not self.embedded)
        side.addWidget(self.label("KOTOBA STUDIO\nFull SDK profile · v0.7.2", "muted"))
        layout.addWidget(sidebar)
        content = QVBoxLayout()
        content.setSpacing(12)
        content.addWidget(self.label(self.t("workspace"), "muted"))
        content.addWidget(self.label(self.t("welcome"), "hero"))
        self.status = self.label(self.t("ready"), "muted")
        content.addWidget(self.status)
        self.add_model_progress(content)
        self.route_label = self.label(self.provider + " · " + self.model, "muted")
        content.addWidget(self.route_label)
        content.addWidget(self.route_controls())
        metrics = QHBoxLayout()
        self.metrics = []
        for key in ("duration", "speed", "rtf"):
            frame = QFrame()
            frame.setObjectName("metric")
            inner = QVBoxLayout(frame)
            inner.setContentsMargins(17, 12, 17, 12)
            inner.addWidget(self.label(self.t(key), "muted"))
            value = self.label("—", "value")
            self.metrics.append(value)
            inner.addWidget(value)
            metrics.addWidget(frame)
        content.addLayout(metrics)
        self.tabs = QTabWidget()
        self.conversation = QTextBrowser()
        self.conversation.setPlainText(self.t("intro"))
        self.tabs.addTab(self.conversation, self.t("conversation"))
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMaximumBlockCount(1000)
        self.tabs.addTab(self.activity, self.t("activity"))
        lab = QWidget()
        lab_layout = QVBoxLayout(lab)
        lab_layout.addWidget(self.label(self.t("reference"), "muted"))
        self.reference = QPlainTextEdit()
        lab_layout.addWidget(self.reference)
        lab_layout.addWidget(self.button("compare", self.compare))
        self.score_label = self.label("WER / CER · —", "muted")
        lab_layout.addWidget(self.score_label)
        self.tabs.addTab(lab, self.t("evaluation"))
        content.addWidget(self.tabs, 1)
        content.addWidget(self.label(self.t("draft"), "muted"))
        self.draft = QPlainTextEdit()
        self.draft.setPlaceholderText(self.t("placeholder"))
        self.draft.setFixedHeight(120)
        content.addWidget(self.draft)
        self.review = self.label(self.t("clean"), "muted")
        content.addWidget(self.review)
        source_row = QHBoxLayout()
        self.audio_source = QComboBox()
        self.audio_source.setMinimumWidth(280)
        self.audio_source.setToolTip("Application selection captures its process tree, including child processes. Browser tabs may share a process. / アプリのプロセスツリーを録音します。")
        source_row.addWidget(self.audio_source, 1)
        self.refresh_sources = QPushButton("↻ Refresh sources" if self.locale == "en" else "↻ 音声入力を更新")
        self.refresh_sources.clicked.connect(self.load_sources)
        source_row.addWidget(self.refresh_sources)
        content.addLayout(source_row)
        self.load_sources()
        copy_row = QHBoxLayout()
        copy_button = QPushButton("Copy reviewed text" if self.locale == "en" else "確認した文をコピー")
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.draft.toPlainText()))
        tidy_button = QPushButton("Tidy spacing" if self.locale == "en" else "空白を整理")
        tidy_button.clicked.connect(lambda: self.draft.setPlainText(format_dictation(self.draft.toPlainText())))
        copy_row.addWidget(copy_button)
        copy_row.addWidget(tidy_button)
        content.addLayout(copy_row)
        phrases = QHBoxLayout()
        self.phrase_button = QPushButton("Saved phrases…" if self.locale == "en" else "定型文を管理…")
        self.phrase_button.clicked.connect(self.edit_snippets)
        self.expand_button = QPushButton("Expand phrases" if self.locale == "en" else "定型文を展開")
        self.expand_button.clicked.connect(self.expand_phrases)
        undo = QPushButton("Undo" if self.locale == "en" else "元に戻す")
        undo.clicked.connect(self.draft.undo)
        phrases.addWidget(self.phrase_button)
        phrases.addWidget(self.expand_button)
        phrases.addWidget(undo)
        content.addLayout(phrases)
        if self.embedded:
            handoff = QPushButton("Copy and open chat →" if self.locale == "en" else "コピーしてチャットを開く →")
            handoff.clicked.connect(self.handoff)
            copy_row.addWidget(handoff)
        controls = QHBoxLayout()
        self.record_button = self.button("record", self.record, "record")
        self.import_button = self.button("import", self.import_audio)
        self.send_button = self.button("send", self.send, "primary")
        controls.addWidget(self.record_button)
        controls.addWidget(self.import_button)
        controls.addStretch()
        controls.addWidget(self.send_button)
        content.addLayout(controls)
        self.speak = QCheckBox(self.t("speak"))
        content.addWidget(self.speak)
        content.addWidget(self.label(self.t("privacy"), "muted"))
        layout.addLayout(content, 1)
        self.setCentralWidget(root)

    def build_compact(self):
        """Capture first, review second; advanced configuration stays out of the draft."""
        from PySide6.QtWidgets import QScrollArea, QLayout, QSizePolicy
        root = QWidget()
        root.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        root.setMinimumHeight(680)
        root.setObjectName("voice-dock")
        root.setStyleSheet("#voice-dock { background: #191a1e; }")
        layout = QVBoxLayout(root)
        layout.setSizeConstraint(QLayout.SetNoConstraint)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        en = self.locale == "en"
        header = QHBoxLayout()
        header.addWidget(self.label("Voice Studio" if en else "音声スタジオ", "hero"), 1)
        self.new_button = self.button("new", self.new_session, "ghost")
        self.new_button.setText("＋")
        self.new_button.setToolTip(self.t("new"))
        self.new_button.setAccessibleName(self.t("new"))
        header.addWidget(self.new_button)
        layout.addLayout(header)
        self.status = self.label(self.t("ready"), "muted")
        layout.addWidget(self.status)
        self.add_model_progress(layout)
        source = QHBoxLayout()
        self.language = QComboBox()
        for name, value in (("日本語", "ja"), ("English", "en"), ("Auto", "auto")):
            self.language.addItem(name, value)
        self.setup_language()
        self.language.setAccessibleName(self.t("lang"))
        self.audio_source = QComboBox()
        self.audio_source.setMinimumWidth(0)
        self.audio_source.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.audio_source.setMinimumContentsLength(12)
        self.audio_source.setAccessibleName("Audio source / 録音元")
        self.refresh_sources = QPushButton("↻")
        self.refresh_sources.setObjectName("ghost")
        self.refresh_sources.setToolTip("Refresh audio sources / 録音元を更新")
        self.refresh_sources.clicked.connect(self.load_sources)
        source.addWidget(self.language)
        source.addWidget(self.audio_source, 1)
        source.addWidget(self.refresh_sources)
        layout.addLayout(source)
        self.load_sources()
        capture = QHBoxLayout()
        self.record_button = self.button("record", self.record, "record")
        self.record_button.setToolTip("Ctrl+Shift+Space")
        self.import_button = self.button("import", self.import_audio)
        capture.addWidget(self.record_button, 1)
        capture.addWidget(self.import_button)
        layout.addLayout(capture)
        layout.addWidget(self.workflow_controls())
        options = QPushButton("Audio settings  ▾" if en else "音声設定  ▾")
        options.setObjectName("ghost")
        options.setCheckable(True)
        layout.addWidget(options, 0, Qt.AlignLeft)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 4)
        self.speech_model = QComboBox()
        self.populate_speech_models()
        self.speech_model.setAccessibleName(self.t("model"))
        advanced_layout.addWidget(self.speech_model)
        self.prepare_button = self.button("prepare", self.prepare)
        advanced_layout.addWidget(self.prepare_button)
        advanced_layout.addWidget(self.label(self.t("privacy"), "micro"))
        advanced.hide()
        options.toggled.connect(advanced.setVisible)
        layout.addWidget(advanced)
        review_header = QHBoxLayout()
        review_header.addWidget(self.label("Review transcript" if en else "文字起こしを確認", "eyebrow"), 1)
        undo = QPushButton("Undo" if en else "元に戻す")
        undo.setObjectName("ghost")
        review_header.addWidget(undo)
        layout.addLayout(review_header)
        self.draft = QPlainTextEdit()
        self.draft.setPlaceholderText("Speak an idea, or type here.\nYou decide what gets sent." if en else "話すか、ここに入力してください。\n送信する内容は自分で確認できます。")
        self.draft.setMinimumHeight(130)
        self.draft.setMaximumHeight(170)
        layout.addWidget(self.draft, 2)
        undo.clicked.connect(self.draft.undo)
        self.review = self.label(self.t("clean"), "micro")
        layout.addWidget(self.review)
        phrases = QHBoxLayout()
        self.phrase_button = QPushButton("Saved phrases" if en else "定型文")
        self.phrase_button.setObjectName("ghost")
        self.phrase_button.clicked.connect(self.edit_snippets)
        self.expand_button = QPushButton("Expand" if en else "展開")
        self.expand_button.setObjectName("ghost")
        self.expand_button.clicked.connect(self.expand_phrases)
        phrases.addWidget(self.phrase_button)
        phrases.addWidget(self.expand_button)
        phrases.addStretch()
        layout.addLayout(phrases)
        self.handoff_button = QPushButton("Add to chat   ↗" if en else "チャットに追加   ↗")
        self.handoff_button.setObjectName("primary")
        self.handoff_button.clicked.connect(self.handoff)
        layout.addWidget(self.handoff_button)
        self.tabs = QTabWidget()
        self.conversation = QTextBrowser()
        self.conversation.setPlainText("Ask the voice agent to work on your reviewed instruction." if en else "確認した指示を音声エージェントに送信できます。")
        agent_page = QWidget()
        agent_layout = QVBoxLayout(agent_page)
        agent_layout.setContentsMargins(0, 8, 0, 0)
        self.route_label = self.label(self.provider + " · " + self.model, "route")
        self.route_label.hide()
        agent_layout.addWidget(self.route_label)
        agent_layout.addWidget(self.route_controls())
        agent_layout.addWidget(self.conversation, 1)
        agent_controls = QHBoxLayout()
        self.send_button = self.button("send", self.send)
        self.send_button.setText("Ask voice agent" if en else "音声エージェントに送信")
        agent_controls.addWidget(self.send_button, 1)
        self.settings_button = self.button("settings", self.settings, "ghost")
        agent_controls.addWidget(self.settings_button)
        agent_layout.addLayout(agent_controls)
        self.tabs.addTab(agent_page, "Agent" if en else "エージェント")
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMaximumBlockCount(1000)
        self.tabs.addTab(self.activity, "Activity" if en else "実行ログ")
        lab = QWidget()
        lab_layout = QVBoxLayout(lab)
        lab_layout.setContentsMargins(0, 8, 0, 0)
        self.reference = QPlainTextEdit()
        self.reference.setPlaceholderText(self.t("reference"))
        lab_layout.addWidget(self.reference)
        lab_layout.addWidget(self.button("compare", self.compare))
        self.score_label = self.label("WER / CER · —", "muted")
        lab_layout.addWidget(self.score_label)
        self.tabs.addTab(lab, "Quality" if en else "精度")
        self.tabs.setMinimumHeight(180)
        layout.addWidget(self.tabs, 2)
        metrics = QHBoxLayout()
        self.metrics = []
        for key in ("duration", "speed", "rtf"):
            metrics.addWidget(self.label(self.t(key), "micro"))
            value = self.label("—", "micro")
            self.metrics.append(value)
            metrics.addWidget(value)
        layout.addLayout(metrics)
        footer = QHBoxLayout()
        self.speak = QCheckBox(self.t("speak"))
        footer.addWidget(self.speak, 1)
        export = self.button("export", self.export, "ghost")
        export.setText("Export" if en else "書き出し")
        footer.addWidget(export)
        layout.addLayout(footer)
        self.locale_button = QPushButton(root)
        self.locale_button.hide()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)


    def selected_config(self):
        return replace(self.config, language=self.language.currentData(), model=self.speech_model.currentData())

    def populate_speech_models(self):
        for model, en, ja in MODEL_CHOICES:
            self.speech_model.addItem(en if self.locale == "en" else ja, model)
        chosen = self.preferences.value("speech/model", "auto")
        self.speech_model.setCurrentIndex(max(0, self.speech_model.findData(chosen)))
        self.speech_model.currentIndexChanged.connect(lambda _: self.preferences.setValue("speech/model", self.speech_model.currentData()))

    def workflow_controls(self):
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        self.global_toggle = QCheckBox("Desktop dictation" if self.locale == "en" else "デスクトップ音声入力")
        self.global_toggle.setChecked(self.global_dictation.enabled)
        self.global_toggle.setToolTip("Uses the selected microphone. Paste replaces the clipboard; never sends Enter. / 選択したマイクを使用。クリップボードを置き換えます。Enter は送信しません。")
        self.global_toggle.toggled.connect(self.toggle_global)
        layout.addWidget(self.global_toggle)
        shortcut = QLabel("Ctrl+Shift+Space · " + ("tap to start / finish" if self.locale == "en" else "押すと開始・終了"))
        shortcut.setObjectName("micro")
        layout.addWidget(shortcut)
        self.meetings_button = QPushButton("Meetings & notes   ↗" if self.locale == "en" else "会議とメモ   ↗")
        self.meetings_button.clicked.connect(self.open_meetings)
        layout.addWidget(self.meetings_button)
        self.processing_button = QPushButton("Processing: " + self.config.processing if self.locale == "en" else "処理方法: " + ("ローカル" if self.config.processing == "local" else "クラウド"))
        self.processing_button.clicked.connect(self.processing_settings)
        layout.addWidget(self.processing_button)
        return box

    def processing_settings(self):
        from .cloud_speech import CloudSpeech
        dialog = QDialog(self)
        dialog.setWindowTitle("Speech processing / 音声処理")
        form = QFormLayout(dialog)
        mode = QComboBox()
        mode.addItem("Local · offline / ローカル · オフライン", "local")
        mode.addItem("Cloud · audio upload / クラウド · 音声を送信", "cloud")
        mode.setCurrentIndex(0 if self.config.processing == "local" else 1)
        endpoint = QLineEdit(self.engine.cloud.endpoint if self.engine.cloud else "https://api.openai.com/v1/audio/transcriptions")
        model = QLineEdit(self.engine.cloud.model if self.engine.cloud else "gpt-4o-transcribe")
        key = QLineEdit(self.engine.cloud.key if self.engine.cloud else "")
        key.setEchoMode(QLineEdit.Password)
        form.addRow("Processing / 処理方法", mode)
        form.addRow("Transcription URL / 文字起こし URL", endpoint)
        form.addRow("Cloud model / クラウドモデル", model)
        form.addRow("API key · this session / 今回のみ", key)
        disclosure = QLabel("Cloud sends recorded audio and glossary to this endpoint. Provider fees and retention apply. Local never falls back to cloud. / クラウドでは録音音声と用語を送信します。提供者の料金・保存規定が適用されます。自動切替はありません。")
        disclosure.setWordWrap(True)
        form.addRow(disclosure)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            try:
                if mode.currentData() == "cloud":
                    self.engine.cloud = CloudSpeech(endpoint.text().strip(), model.text().strip(), key.text().strip())
                else:
                    self.engine.cloud = None
                self.config = replace(self.config, processing=mode.currentData())
                self.processing_button.setText("Processing: " + self.config.processing if self.locale == "en" else "処理方法: " + ("ローカル" if self.config.processing == "local" else "クラウド"))
            except ValueError as error:
                self.failure(str(error))

    def toggle_global(self, enabled):
        try:
            self.global_dictation.set_enabled(enabled)
        except RuntimeError as error:
            self.global_toggle.blockSignals(True)
            self.global_toggle.setChecked(False)
            self.global_toggle.blockSignals(False)
            self.failure(str(error))

    def open_meetings(self):
        from .meetings_ui import MeetingsDialog
        dialog = MeetingsDialog(self)
        dialog.exec()
        dialog.deleteLater()

    def load_sources(self):
        selected = self.audio_source.currentData()
        self.audio_source.clear()
        for source in sources():
            self.audio_source.addItem(source.label, source)
            if source == selected:
                self.audio_source.setCurrentIndex(self.audio_source.count() - 1)

    def busy(self, value):
        self.busy_changed.emit(value)
        for widget in (self.record_button, self.import_button, self.send_button, self.prepare_button,
                       self.settings_button, self.new_button, self.locale_button, self.language, self.speech_model,
                       self.audio_source, self.refresh_sources, self.phrase_button, self.expand_button,
                       self.global_toggle, self.meetings_button, self.processing_button,
                       self.agent_provider, self.agent_model, self.refresh_routes_button):
            widget.setEnabled(not value)
        if not value:
            route = next((r for r in self.routes if r["id"] == self.provider), None)
            self.agent_model.setEnabled(bool(route and route["configured"]))

    def work(self, task, result):
        if self.job is not None:
            return
        self.download_progress.hide()
        self.busy(True)
        self.status.setText(self.t("working"))
        self.job = Job(task)
        self.job.result.connect(result)
        self.job.failure.connect(self.failure)
        self.job.activity.connect(self.activity.appendPlainText)
        self.job.finished.connect(self.finished)
        self.job.start()

    def finished(self):
        job = self.job
        self.job = None
        job.deleteLater()
        self.busy(False)
        if self.status.text() == self.t("working"):
            self.status.setText(self.t("ready"))
        continuation, self.after_job = self.after_job, None
        if continuation is not None:
            continuation()

    def failure(self, message):
        self.download_progress.hide()
        # Runtime diagnostics can contain provider details; never export them automatically.
        if self.api_key:
            message = message.replace(self.api_key, "[redacted]")
        if self.engine.cloud:
            message = message.replace(self.engine.cloud.key, "[redacted]")
        env_key = os.environ.get("DEEPSEEK_API_KEY")
        if env_key:
            message = message.replace(env_key, "[redacted]")
        self.status.setText(self.t("error"))
        if self.global_dictation.target:
            self.global_dictation.target = None
            self.global_dictation.notice("Dictation failed · open Voice Studio", "音声入力に失敗 · 音声スタジオを確認")
            self.activity.appendPlainText(message[:2000])
            return
        QMessageBox.warning(self, self.t("error"), message[:2000])

    def prepare(self):
        config = self.selected_config()
        self.prepare_model(config)

    def add_model_progress(self, layout):
        self.download_progress = QProgressBar()
        self.download_progress.setAccessibleName("Model setup progress" if self.locale == "en" else "モデル準備の進捗")
        self.download_progress.setMinimumHeight(22)
        self.download_progress.hide()
        layout.addWidget(self.download_progress)

    @Slot(object)
    def show_model_progress(self, progress):
        en = self.locale == "en"
        labels = {"checking": ("Checking model files…", "モデルファイルを確認中…"),
                  "downloading": ("Downloading model…", "モデルをダウンロード中…"),
                  "extracting": ("Unpacking model…", "モデルを展開中…"),
                  "loading": ("Loading model…", "モデルを読み込み中…")}
        label = labels[progress.phase][0 if en else 1]
        bar = self.download_progress
        bar.show()
        if progress.total > 0:
            bar.setRange(0, 1000)
            bar.setValue(min(1000, int(progress.completed * 1000 / progress.total)))
            if progress.unit == "bytes":
                detail = f"{progress.completed / 1048576:.1f} / {progress.total / 1048576:.1f} MiB"
            else:
                detail = f"{progress.completed} / {progress.total} " + ("files" if en else "ファイル")
            bar.setFormat(f"%p% · {detail}")
        else:
            bar.setRange(0, 0)
            detail = (f"{progress.completed / 1048576:.1f} MiB" if progress.completed else "")
        self.status.setText(label + (f" · {detail}" if detail else ""))

    def prepare_model(self, config):
        if self.job is not None:
            return
        def ready(_):
            self.download_progress.setRange(0, 100)
            self.download_progress.setValue(100)
            self.download_progress.setFormat(self.t("prepared"))
            self.download_progress.show()
            self.status.setText("Model ready · press Record to start" if self.locale == "en" else "準備完了 · 録音を押してください")
        self.work(lambda emit: self.engine.prepare(config, allow_download=True,
                                                  progress=self.model_progress.emit), ready)
        from .model_progress import ModelProgress
        self.show_model_progress(ModelProgress("checking"))

    def ensure_speech(self, ready):
        """Check local files on the worker before opening any audio stream."""
        config = self.selected_config()
        def check(emit):
            try:
                self.engine.prepare(config, allow_download=False)
            except ModelDownloadRequired as missing:
                return missing
            return None
        def checked(missing):
            self.after_job = (lambda: self.offer_model_download(config, missing.model)) if missing else ready
        self.work(check, checked)

    def offer_model_download(self, config, model):
        # Setup may change foreground focus; a later hotkey must capture a new target.
        self.global_dictation.target = None
        self.global_dictation.overlay.hide()
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Set up voice" if self.locale == "en" else "音声機能を準備")
        dialog.setText("Download your speech model first" if self.locale == "en" else "最初に音声モデルをダウンロードしてください")
        dialog.setInformativeText((f"{model}\n\nModel files will be downloaded to this computer. Your audio is not uploaded. The download may be large and take several minutes. After setup, press Record again; local transcription works offline.\n\nChange Input language or Speech model in Audio settings to choose a different model."
            if self.locale == "en" else f"{model}\n\nモデルをこの端末にダウンロードします。音声は送信されません。大きなファイルのため数分かかる場合があります。完了後に再度録音を押してください。文字起こしはオフラインで動作します。\n\n音声設定の入力言語・音声モデルで別のモデルを選べます。"))
        download = dialog.addButton("Download model" if self.locale == "en" else "モデルをダウンロード", QMessageBox.AcceptRole)
        dialog.addButton(QMessageBox.Cancel)
        dialog.exec()
        if dialog.clickedButton() == download:
            self.prepare_model(config)
        else:
            self.status.setText(self.t("configure"))

    def record(self):
        if self.job is not None:
            return
        if self.stream is not None:
            self.timer.stop()
            self.stream.stop()
            self.record_error = getattr(self.stream, "error", "") or self.record_error
            self.stream.close()
            self.stream = None
            self.record_button.setText(self.t("record"))
            if self.record_error:
                self.busy(False)
                self.failure(self.record_error)
                self.frames = []
                return
            audio = np.concatenate(self.frames) if self.frames else np.array([], dtype=np.float32)
            self.frames = []
            if audio.size == 0:
                self.busy(False)
                self.failure("No audio was captured. Check your input and try again." if self.locale == "en" else "音声を取得できませんでした。入力を確認して、もう一度お試しください。")
                return
            self.transcribe(audio)
            return
        self.ensure_speech(self.start_recording)

    def start_recording(self):
        self.tts.stop()
        self.frames = []
        self.record_error = ""
        def capture(data, count, timing, status):
            if status:
                self.record_error = str(status)
            if sum(len(frame) for frame in self.frames) < 16000 * 60:
                self.frames.append(data[:, 0].copy())
        try:
            import sounddevice as sd
            source = self.audio_source.currentData()
            if source is None:
                raise ValueError("Choose an audio input before recording." if self.locale == "en" else "録音する前に音声入力を選択してください。")
            if source.kind == "microphone":
                self.stream = sd.InputStream(device=source.device, samplerate=16000, channels=1, dtype="float32", callback=capture)
            else:
                self.stream = LoopbackStream(source, capture)
            self.stream.start()
        except Exception as error:
            if self.stream is not None:
                self.stream.close()
            self.stream = None
            self.failure(str(error))
            return
        self.busy(True)
        self.record_button.setEnabled(True)
        self.record_button.setText(self.t("stop"))
        self.status.setText(self.t("recording"))
        if self.global_dictation.target:
            self.global_dictation.notice("Listening · Ctrl+Shift+Space to finish", "録音中 · Ctrl+Shift+Space で終了", True)
        self.timer.start(60000)

    def import_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t("import"), "", "Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.webm)")
        if path:
            config = self.selected_config()
            self.ensure_speech(lambda: self.work(lambda emit: self.engine.transcribe(load_audio(path, config.max_seconds), config), self.transcribed))

    def transcribe(self, audio):
        config = self.selected_config()
        self.work(lambda emit: self.engine.transcribe(audio, config), self.transcribed)

    def transcribed(self, result):
        self.last_transcript = result
        self.draft.setPlainText(result.text)
        for widget, text in zip(self.metrics, (f"{result.duration_seconds:.1f}s", f"{result.latency_seconds:.2f}s", f"{result.real_time_factor:.2f}×")):
            widget.setText(text)
        self.review.setText(self.t("review") + " · " + ", ".join(result.review_reasons) if result.review_reasons else self.t("clean"))
        self.status.setText(self.t("ready") if result.text else self.t("empty"))
        self.entries.append({"kind": "transcription", "time": datetime.now(timezone.utc).isoformat(), **result.to_dict()})
        self.global_dictation.deliver(result)

    def send(self):
        text = self.draft.toPlainText().strip()
        if not text:
            return
        self.tts.stop()
        route = next((r for r in self.routes if r["id"] == self.provider and r["configured"]), None)
        if route is None or not self.model:
            self.failure("Select a configured provider and model. Refresh models after configuring Chat Settings → Models. / チャット設定で接続先を設定し、モデル一覧を更新してください。")
            return
        workspace, model, key, provider = self.workspace, self.model, self.api_key, self.provider
        key_ref = route["key_ref"]
        def run(emit):
            started = perf_counter()
            def notify(notification):
                params = notification.payload
                event = params.get("event", {})
                emit(str(event.get("type", notification.method)))
            result = self.harness.run(text, workspace, model, key, notify, provider=provider, key_ref=key_ref)
            return text, result, perf_counter() - started
        self.work(run, self.responded)

    def responded(self, payload):
        text, result, latency = payload
        if not any(entry["kind"] == "turn" for entry in self.entries):
            self.conversation.clear()
        # Plain text prevents model output from creating active HTML resources or links.
        self.conversation.append(self.t("you"))
        self.conversation.insertPlainText("\n" + text + "\n\n" + self.t("result") + "\n" + result.final_response + "\n\n")
        self.last_reply = result.final_response
        self.entries.append({"kind": "turn", "session_id": result.session_id, "prompt": text,
                             "reply": result.final_response, "latency_seconds": latency, "finish_reason": result.finish_reason,
                             "event_count": len(result.events)})
        self.draft.clear()
        self.status.setText(f"{self.t('ready')} · {latency:.1f}s · {len(result.events)} {self.t('events')}")
        if self.speak.isChecked():
            self.read_reply()

    def read_reply(self):
        lang = "ja" if any("\u3040" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff" for c in self.last_reply) else "en"
        voice = next((v for v in self.tts.availableVoices() if v.locale().name().startswith(lang)), None)
        if voice is None:
            self.status.setText(self.t("no_voice"))
            return
        self.tts.setVoice(voice)
        self.tts.say(self.last_reply[:6000])

    def compare(self):
        reference, hypothesis = self.reference.toPlainText(), self.draft.toPlainText()
        if not reference or not hypothesis:
            self.score_label.setText(self.t("no_ref"))
            return
        lang = self.language.currentData()
        result = score(reference, hypothesis, "mixed" if lang == "auto" else lang)
        rate = f"{result['error_rate']:.2%}" if result['error_rate'] is not None else "—"
        self.score_label.setText(f"{result['metric']}: {rate} · {result['errors']} / {result['reference_units']}")

    def export(self):
        if not self.entries:
            self.status.setText(self.t("no_export"))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.t("export"), "kotoba-session.json", "JSON (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps({"version": 1, "entries": self.entries}, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError as error:
                self.failure(str(error))

    def new_session(self):
        self.work(lambda emit: self.harness.close(), lambda _: self.reset_session())

    def reset_session(self):
        self.entries = []
        self.last_transcript = None
        self.last_reply = ""
        self.draft.clear()
        self.activity.clear()
        self.conversation.setPlainText(self.t("intro"))
        self.status.setText(self.t("ready"))

    def switch_locale(self):
        self.set_locale("en" if self.locale == "ja" else "ja")

    def set_locale(self, locale):
        if locale == self.locale or locale not in COPY or self.job is not None or self.stream is not None:
            return
        draft, conversation, activity = self.draft.toPlainText(), self.conversation.toPlainText(), self.activity.toPlainText()
        reference, score_text = self.reference.toPlainText(), self.score_label.text()
        metrics = [metric.text() for metric in self.metrics]
        audio_source = self.audio_source.currentData()
        language, model = self.language.currentIndex(), self.speech_model.currentIndex()
        spoken, tab = self.speak.isChecked(), self.tabs.currentIndex()
        self.locale = locale
        self.preferences.setValue("locale", locale)
        self.build()
        self.draft.setPlainText(draft)
        if self.entries:
            self.conversation.setPlainText(conversation)
        self.activity.setPlainText(activity)
        self.language.setCurrentIndex(language)
        self.speech_model.setCurrentIndex(model)
        self.reference.setPlainText(reference)
        self.score_label.setText(score_text)
        self.speak.setChecked(spoken)
        self.tabs.setCurrentIndex(tab)
        if self.last_transcript:
            self.review.setText(self.t("review") + " · " + ", ".join(self.last_transcript.review_reasons)
                               if self.last_transcript.review_reasons else self.t("clean"))
        for metric, text in zip(self.metrics, metrics):
            metric.setText(text)
        for index in range(self.audio_source.count()):
            if self.audio_source.itemData(index) == audio_source:
                self.audio_source.setCurrentIndex(index)
        self.locale_changed.emit(locale)

    def expand_phrases(self):
        """Keep the raw transcript in session evidence; expansion is one undoable edit."""
        text = self.draft.toPlainText()
        expanded = expand_snippets(text, self.snippets)
        if expanded != text:
            cursor = self.draft.textCursor()
            cursor.beginEditBlock()
            cursor.select(QTextCursor.Document)
            cursor.insertText(expanded)
            cursor.endEditBlock()
        self.review.setText(self.t("clean"))

    def handoff(self):
        text = self.draft.toPlainText().strip()
        if text:
            self.draft_handoff.emit(text)

    def edit_snippets(self):
        if self.snippet_error:
            self.failure(self.snippet_error)
            return
        def tr(en, ja):
            return en if self.locale == "en" else ja
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Saved phrases", "定型文"))
        dialog.resize(720, 620)
        layout = QVBoxLayout(dialog)
        hint = QLabel(tr("Say a short trigger, then choose Expand phrases before sending. Japanese triggers must be separated by punctuation or spaces. Saved locally; never sent automatically.",
                         "短い合図を話し、送信前に「定型文を展開」を押します。日本語の合図は句読点や空白で区切ってください。端末内に保存し、自動送信しません。"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        items = [dict(item) for item in self.snippets]
        listing = QListWidget()
        layout.addWidget(listing)
        trigger = QLineEdit()
        trigger.setMaxLength(100)
        trigger.setPlaceholderText(tr("Trigger, e.g. meeting template", "合図（例：議事録テンプレート）"))
        replacement = QPlainTextEdit()
        replacement.setPlaceholderText(tr("Expanded text, including multiple lines", "展開する文章（複数行可）"))
        layout.addWidget(trigger)
        layout.addWidget(replacement)
        message = QLabel()
        message.setWordWrap(True)
        layout.addWidget(message)
        def refresh():
            listing.clear()
            listing.addItems([item["trigger"] for item in items])
        def select(row):
            if 0 <= row < len(items):
                trigger.setText(items[row]["trigger"])
                replacement.setPlainText(items[row]["replacement"])
        listing.currentRowChanged.connect(select)
        refresh()
        def apply_item():
            from .snippets import validate_snippets
            row = listing.currentRow()
            updated = [dict(item) for item in items]
            item = {"trigger": trigger.text(), "replacement": replacement.toPlainText()}
            if row >= 0:
                updated[row] = item
            else:
                updated.append(item)
            try:
                checked = validate_snippets(updated)
            except ValueError as error:
                message.setText(str(error))
                return
            items[:] = checked
            refresh()
            trigger.clear()
            replacement.clear()
            message.setText(tr("Phrase applied. Save to keep changes.", "定型文を反映しました。保存すると確定します。"))
        def new():
            listing.setCurrentRow(-1)
            trigger.clear()
            replacement.clear()
        def remove():
            row = listing.currentRow()
            if row >= 0:
                items.pop(row)
                refresh()
                new()
        row = QHBoxLayout()
        for caption, action in [(tr("New", "新規"), new), (tr("Apply phrase", "定型文を反映"), apply_item), (tr("Delete", "削除"), remove)]:
            button = QPushButton(caption)
            button.clicked.connect(action)
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(tr("Save", "保存"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("Cancel", "キャンセル"))
        def save():
            # Require explicit application so an unfinished edit is never silently lost.
            selected = listing.currentRow()
            current = items[selected] if selected >= 0 else {"trigger": "", "replacement": ""}
            if trigger.text() != current["trigger"] or replacement.toPlainText() != current["replacement"]:
                message.setText(tr("Apply the edited phrase before saving.", "編集中の定型文を反映してから保存してください。"))
                return
            try:
                save_snippets(self.home / "snippets.json", items)
            except (OSError, ValueError) as error:
                message.setText(str(error))
                return
            self.snippets = items
            dialog.accept()
        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def settings(self):
        if self.runtime_url:
            def loaded(routes):
                self.apply_routes(routes)
                self.after_job = self.settings_dialog
            self.work(lambda emit: load_routes(self.runtime_url), loaded)
        else:
            self.settings_dialog()

    def settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("settings"))
        dialog.setMinimumWidth(560)
        form = QFormLayout(dialog)
        key = QLineEdit(self.api_key)
        key.setEchoMode(QLineEdit.Password)
        key.setPlaceholderText("Uses saved provider credentials / 保存済みの認証情報を使用")
        model = QComboBox()
        model.setEditable(True)
        model.setInsertPolicy(QComboBox.NoInsert)
        model.lineEdit().setMaxLength(512)
        provider = QComboBox()
        for route in self.routes:
            provider.addItem(route["name"], route["id"])
        provider.setCurrentIndex(provider.findData(self.provider))
        def changed(*_):
            route = next((r for r in self.routes if r["id"] == provider.currentData()), None)
            model.clear()
            key.clear()
            if route:
                model.addItems([m["id"] for m in route["models"]])
                model.setEnabled(route["configured"])
                key.setEnabled(bool(route["key_ref"]))
        provider.currentIndexChanged.connect(changed)
        changed()
        if provider.currentData() == self.provider:
            model.setCurrentText(self.model)
            key.setText(self.api_key)
        hint = QLabel("Add providers and API keys in Chat Settings → Models, then reopen these settings." if self.locale == "en" else "チャット設定のモデル画面で接続先と API キーを追加し、この設定を開き直してください。")
        hint.setWordWrap(True)
        form.addRow(hint)
        form.addRow("Provider" if self.locale == "en" else "接続先", provider)
        workspace = QLineEdit(self.workspace)
        browse = self.button("browse", lambda: workspace.setText(QFileDialog.getExistingDirectory(dialog, self.t("folder"), workspace.text()) or workspace.text()))
        glossary = QLineEdit(self.config.glossary)
        glossary.setMaxLength(1000)
        device = QComboBox()
        device.addItems(["cpu", "cuda"])
        device.setCurrentText(self.config.device)
        for label, widget in (("key", key), ("llm", model), ("folder", workspace), ("browse", browse), ("glossary", glossary), ("device", device)):
            form.addRow(self.t(label), widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            self.api_key, self.model, self.workspace = key.text().strip(), model.currentText().strip(), workspace.text()
            self.provider = provider.currentData() or ""
            self.preferences.setValue("voice/model_provider", self.provider)
            self.apply_routes(self.routes)
            self.preferences.setValue("voice/provider", self.provider)
            self.preferences.setValue("voice/model", self.model)
            self.route_label.setText(self.provider + " · " + self.model)
            self.config = replace(self.config, glossary=glossary.text(), device=device.currentText(), compute_type="float16" if device.currentText() == "cuda" else "int8")

    def closeEvent(self, event):
        if self.job is not None or self.stream is not None:
            self.status.setText(self.t("busy_close"))
            event.ignore()
            return
        self.tts.stop()
        self.global_dictation.close()
        self.harness.close()
        event.accept()


def main():
    from .branding import configure_windows_identity
    configure_windows_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("Kotoba")
    app.setOrganizationName("Kotoba")
    app.setApplicationDisplayName("Kotoba Studio")
    app.setWindowIcon(QIcon(str(icon_path())))
    app.setFont(QFont("Yu Gothic UI", 10))
    window = Window()
    window.show()
    if "--smoke" in sys.argv:
        def capture():
            output = Path(os.environ.get("KOTOBA_SCREENSHOT", "kotoba-smoke.png"))
            window.grab().save(str(output))
            window.close()
        QTimer.singleShot(700, capture)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
