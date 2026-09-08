"""Native bilingual desktop voice workspace with an explicit review boundary."""

from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QStandardPaths
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTextBrowser,
    QVBoxLayout, QWidget)
from PySide6.QtTextToSpeech import QTextToSpeech

from .harness import HarnessSession
from .speech import SpeechConfig, SpeechEngine, load_audio
from .evaluate import score


COPY = {
    "en": {
        "tagline": "Your voice. The full power of Harness.", "workspace": "VOICE WORKSPACE",
        "record": "●  Record", "stop": "■  Transcribe", "import": "Import audio", "send": "Send reviewed text  →",
        "draft": "TRANSCRIPT · REVIEW BEFORE SENDING", "placeholder": "Speak in Japanese or English, import a recording, or type here…",
        "conversation": "Conversation", "activity": "Harness activity", "evaluation": "Accuracy lab",
        "ready": "Ready to listen", "recording": "Recording locally · 60 second limit", "working": "Working…",
        "privacy": "Audio stays local. Reviewed text goes to your model provider and Harness history.",
        "settings": "Settings", "new": "+ New session", "export": "Export session", "speak": "Read reply aloud",
        "welcome": "Speak naturally. Act deliberately.", "intro": "Japanese and English voice input, with the complete DeepSeek agent runtime behind it.\n\n1   Record or import audio\n2   Review names, numbers, and intent\n3   Send your instruction to Harness",
        "model": "Speech model", "lang": "Input language", "speed": "INFERENCE", "duration": "AUDIO", "rtf": "REAL-TIME FACTOR",
        "review": "Review required", "clean": "Check names and numbers before sending.", "reference": "Human-checked reference",
        "compare": "Compare with transcript", "no_ref": "Enter a reference and transcript first.",
        "configure": "Model weights download on first use. Large-v3 prioritizes quality; CPU inference can be slow.",
        "key": "API key (this session only)", "llm": "Harness model", "folder": "Agent workspace", "browse": "Choose folder",
        "glossary": "Names and technical terms (optional)", "device": "Inference device", "save": "Apply", "error": "Action could not complete",
        "busy_close": "Wait for the current operation to finish before closing. No agent request will be replayed automatically.",
        "no_voice": "No installed voice matches the reply language. Install a Japanese/English Windows speech voice.",
        "empty": "No speech detected. Try again closer to the microphone.", "prepared": "Model ready", "prepare": "Download / warm model",
        "result": "Reply", "you": "You", "events": "Events", "no_export": "There is no session data to export yet.",
    },
    "ja": {
        "tagline": "声でつながる、Harness のすべての力。", "workspace": "音声ワークスペース",
        "record": "●  録音", "stop": "■  文字起こし", "import": "音声を読み込む", "send": "確認した内容を送信  →",
        "draft": "文字起こし · 送信前に確認", "placeholder": "日本語・英語で話す、音声を読み込む、または入力してください…",
        "conversation": "会話", "activity": "Harness の動作", "evaluation": "精度ラボ",
        "ready": "録音できます", "recording": "ローカル録音中 · 最大60秒", "working": "処理中…",
        "privacy": "音声は端末内で処理します。送信したテキストはモデル提供者と Harness の履歴に渡ります。",
        "settings": "設定", "new": "+ 新しい会話", "export": "会話をエクスポート", "speak": "返答を読み上げる",
        "welcome": "自然に話して、確かめて実行。", "intro": "日本語と英語の音声入力を、DeepSeek のエージェント機能につなげます。\n\n1   録音する、または音声を読み込む\n2   名前・数字・意図を確認する\n3   Harness に指示を送信する",
        "model": "音声モデル", "lang": "入力言語", "speed": "処理時間", "duration": "音声の長さ", "rtf": "実時間比",
        "review": "確認が必要です", "clean": "送信前に名前と数字を確認してください。", "reference": "人手で確認した正解文",
        "compare": "文字起こしと比較", "no_ref": "正解文と文字起こしを入力してください。",
        "configure": "初回はモデルをダウンロードします。Large-v3 は精度重視の候補です。CPUでは時間がかかります。",
        "key": "APIキー（今回のみ）", "llm": "Harness モデル", "folder": "作業フォルダー", "browse": "フォルダーを選ぶ",
        "glossary": "名前・専門用語（任意）", "device": "処理デバイス", "save": "適用", "error": "処理を完了できませんでした",
        "busy_close": "処理の完了後に終了してください。エージェントへの指示は自動で再送されません。",
        "no_voice": "返答の言語に対応する音声がありません。Windowsの日本語・英語音声をインストールしてください。",
        "empty": "音声が検出されませんでした。マイクに近づいて再度お試しください。", "prepared": "モデルを準備しました", "prepare": "モデルを準備",
        "result": "返答", "you": "あなた", "events": "イベント", "no_export": "まだエクスポートするデータがありません。",
    },
}

STYLE = """
QMainWindow, QDialog { background:#101416; color:#e8eeeb; }
QWidget { color:#e8eeeb; font-family:'Segoe UI','Yu Gothic UI'; font-size:14px; }
QLabel#brand {font-size:29px; font-weight:700; color:#e3f3e9;}
QLabel#muted {color:#91a69d; font-size:12px;}
QLabel#hero {font-size:25px; font-weight:600;}
QFrame#sidebar {background:#171e1d; border-radius:15px;}
QFrame#metric {background:#1b2522; border:1px solid #2b3b34; border-radius:12px;}
QLabel#value {font-size:24px; color:#b3e8ca; font-weight:600;}
QPushButton {background:#24342d; border:1px solid #3a5145; border-radius:8px; padding:11px 16px;}
QPushButton:hover {background:#314b3c; border-color:#8dccaa;}
QPushButton:disabled {color:#62736a; background:#1c2520; border-color:#26372e;}
QPushButton#primary {background:#c8ecd5; color:#163826; font-weight:700; border:0;}
QPushButton#record {background:#5b332e; border-color:#bd776c;}
QPlainTextEdit, QTextBrowser, QLineEdit {background:#181f20; border:1px solid #34433b; border-radius:10px; padding:12px; selection-background-color:#436950;}
QComboBox {background:#1d2b24; border:1px solid #3c5044; border-radius:7px; padding:9px;}
QComboBox QAbstractItemView {background:#1d2b24; selection-background-color:#3c5044;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:#101416; color:#879b91; padding:12px 18px; border-bottom:2px solid #26352e;}
QTabBar::tab:selected {color:#d5ebdf; border-bottom:2px solid #c8ecd5;}
QCheckBox {spacing:8px; color:#aebfb5;}
QSplitter::handle {background:#26352e; width:1px;}
"""


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
    def __init__(self):
        super().__init__()
        self.locale = "ja"
        self.home = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.home.mkdir(parents=True, exist_ok=True)
        self.engine = SpeechEngine(self.home / "models")
        self.harness = HarnessSession(self.home / "harness")
        self.config = SpeechConfig()
        self.api_key = ""
        self.model = "deepseek-v4-flash"
        self.workspace = str(self.home / "workspace")
        Path(self.workspace).mkdir(exist_ok=True)
        self.job = None
        self.stream = None
        self.frames = []
        self.record_error = ""
        self.last_transcript = None
        self.last_reply = ""
        self.entries = []
        self.tts = QTextToSpeech(self)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.record)
        self.setWindowTitle("Kotoba · ことば — DeepSeek Harness")
        self.resize(1360, 890)
        self.setMinimumSize(1080, 740)
        self.setStyleSheet(STYLE)
        self.build()

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
        side.addWidget(self.language)
        side.addWidget(self.label(self.t("model"), "muted"))
        self.speech_model = QComboBox()
        self.speech_model.addItem("Large-v3 · Quality", "large-v3")
        self.speech_model.addItem("Turbo · Speed", "turbo")
        side.addWidget(self.speech_model)
        self.prepare_button = self.button("prepare", self.prepare)
        side.addWidget(self.prepare_button)
        side.addWidget(self.label(self.t("configure"), "muted"))
        side.addStretch()
        self.settings_button = self.button("settings", self.settings)
        side.addWidget(self.settings_button)
        side.addWidget(self.button("export", self.export))
        switch = QPushButton("日本語  ⇄  English")
        switch.clicked.connect(self.switch_locale)
        self.locale_button = switch
        side.addWidget(switch)
        side.addWidget(self.label("DEEPSEEK HARNESS\nFull SDK profile · v0.1.0", "muted"))
        layout.addWidget(sidebar)
        content = QVBoxLayout()
        content.setSpacing(16)
        content.addWidget(self.label(self.t("workspace"), "muted"))
        content.addWidget(self.label(self.t("welcome"), "hero"))
        self.status = self.label(self.t("ready"), "muted")
        content.addWidget(self.status)
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

    def selected_config(self):
        return replace(self.config, language=self.language.currentData(), model=self.speech_model.currentData())

    def busy(self, value):
        for widget in (self.record_button, self.import_button, self.send_button, self.prepare_button,
                       self.settings_button, self.new_button, self.locale_button, self.language, self.speech_model):
            widget.setEnabled(not value)

    def work(self, task, result):
        if self.job is not None:
            return
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

    def failure(self, message):
        # Runtime diagnostics can contain provider details; never export them automatically.
        if self.api_key:
            message = message.replace(self.api_key, "[redacted]")
        env_key = os.environ.get("DEEPSEEK_API_KEY")
        if env_key:
            message = message.replace(env_key, "[redacted]")
        self.status.setText(self.t("error"))
        QMessageBox.warning(self, self.t("error"), message[:2000])

    def prepare(self):
        config = self.selected_config()
        self.work(lambda emit: self.engine.prepare(config), lambda _: self.status.setText(self.t("prepared")))

    def record(self):
        if self.stream is not None:
            self.timer.stop()
            self.stream.stop()
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
            self.transcribe(audio)
            return
        self.tts.stop()
        self.frames = []
        self.record_error = ""
        def capture(data, count, timing, status):
            if status:
                self.record_error = str(status)
            self.frames.append(data[:, 0].copy())
        try:
            import sounddevice as sd
            self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=capture)
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
        self.timer.start(60000)

    def import_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t("import"), "", "Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.webm)")
        if path:
            config = self.selected_config()
            self.work(lambda emit: self.engine.transcribe(load_audio(path, config.max_seconds), config), self.transcribed)

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

    def send(self):
        text = self.draft.toPlainText().strip()
        if not text:
            return
        self.tts.stop()
        workspace, model, key = self.workspace, self.model, self.api_key
        def run(emit):
            started = perf_counter()
            def notify(notification):
                params = notification.payload
                event = params.get("event", {})
                emit(str(event.get("type", notification.method)))
            result = self.harness.run(text, workspace, model, key, notify)
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
        draft, conversation, activity = self.draft.toPlainText(), self.conversation.toPlainText(), self.activity.toPlainText()
        language, model = self.language.currentIndex(), self.speech_model.currentIndex()
        self.locale = "en" if self.locale == "ja" else "ja"
        self.build()
        self.draft.setPlainText(draft)
        if self.entries:
            self.conversation.setPlainText(conversation)
        self.activity.setPlainText(activity)
        self.language.setCurrentIndex(language)
        self.speech_model.setCurrentIndex(model)

    def settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("settings"))
        dialog.setMinimumWidth(560)
        form = QFormLayout(dialog)
        key = QLineEdit(self.api_key)
        key.setEchoMode(QLineEdit.Password)
        model = QLineEdit(self.model)
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
            self.api_key, self.model, self.workspace = key.text().strip(), model.text().strip(), workspace.text()
            self.config = replace(self.config, glossary=glossary.text(), device=device.currentText(), compute_type="float16" if device.currentText() == "cuda" else "int8")

    def closeEvent(self, event):
        if self.job is not None or self.stream is not None:
            self.status.setText(self.t("busy_close"))
            event.ignore()
            return
        self.tts.stop()
        self.harness.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Kotoba")
    app.setOrganizationName("Kotoba")
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
