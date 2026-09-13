"""Voice and text in one native conversation, with an explicit agent handoff."""

import base64
import os
import sys
import uuid

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPlainTextEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget)

from .audio_sources import sources
from .live_protocol import PROVIDERS, VoiceProtocol
from .live_voice import LiveVoice
from .messaging_store import protect
from .selection_widgets import ClickComboBox


class LiveVoicePanel(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.session = None
        self.messages = {}
        self.failed = False
        self.translations = []
        self.elapsed = 0
        self.conversation_provider = ""
        self.build()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)

    def tr(self, en, ja):
        return en if self.owner.locale == "en" else ja

    def label(self, en, ja, layout):
        label = QLabel(self.tr(en, ja))
        label.setWordWrap(True)
        self.translations.append((label.setText, en, ja))
        layout.addWidget(label)
        return label

    def button(self, en, ja, callback):
        button = QPushButton(self.tr(en, ja))
        self.translations.append((button.setText, en, ja))
        button.clicked.connect(callback)
        return button

    def build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = self.label("Talk it through", "ことばで、一緒に考える", heading)
        title.setStyleSheet("font-size:20px;font-weight:600;color:#e5eee9")
        heading.addStretch()
        close = QPushButton("×")
        close.setFixedSize(30, 30)
        close.setAccessibleName(self.tr("Close voice panel", "音声パネルを閉じる"))
        close.clicked.connect(self.owner.dock_close_requested.emit)
        heading.addWidget(close)
        layout.addLayout(heading)
        self.label("Speak, type, and explore ideas in the same conversation.", "話すことも、入力することも。ひとつの会話で考えを深めましょう。", layout)
        setup = QWidget()
        setup_layout = QVBoxLayout(setup)
        setup_layout.setContentsMargins(0, 0, 0, 0)
        setup_layout.setSpacing(10)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setSpacing(6)
        self.provider = ClickComboBox()
        for identity, provider in PROVIDERS.items():
            self.provider.addItem(provider.name, identity)
        preferred = self.owner.preferences.value("live/provider", "openai")
        self.provider.setCurrentIndex(max(0, self.provider.findData(preferred)))
        self.model = QLineEdit()
        self.model.setMaxLength(128)
        self.voice = ClickComboBox()
        self.language = ClickComboBox()
        for label, code in (("English", "en"), ("日本語", "ja"), ("English ↔ 日本語", "auto")):
            self.language.addItem(label, code)
        self.language.setCurrentIndex(max(0, self.language.findData(self.owner.locale)))
        self.microphones = ClickComboBox()
        self.microphones.setMinimumWidth(0)
        self.microphones.setSizeAdjustPolicy(ClickComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.microphones.setMinimumContentsLength(15)
        self.refresh = self.button("Refresh microphones", "マイク一覧を更新", self.refresh_microphones)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setMaxLength(4096)
        self.key.setPlaceholderText(self.tr("API key · used only for this provider", "API キー · この接続先でのみ使用"))
        self.translations.append((self.key.setPlaceholderText, "API key · used only for this provider", "API キー · この接続先でのみ使用"))
        self.remember = QCheckBox(self.tr("Remember key on this Windows account", "この Windows アカウントにキーを保存"))
        self.translations.append((self.remember.setText, "Remember key on this Windows account", "この Windows アカウントにキーを保存"))
        self.remember.setEnabled(sys.platform == "win32")
        self.forget = self.button("Forget saved key", "保存したキーを削除", self.forget_key)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_form = QFormLayout()
        advanced_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        advanced_layout.addLayout(advanced_form)
        for widget, en, ja in ((self.provider, "Voice provider", "音声の接続先"),
                (self.model, "Voice model", "音声モデル"), (self.voice, "Voice", "声"),
                (self.language, "Conversation language", "会話の言語"), (self.microphones, "Microphone", "マイク"),
                (self.key, "Voice API key", "音声 API キー")):
            label = QLabel(self.tr(en, ja))
            self.translations.append((label.setText, en, ja))
            widget.setAccessibleName(label.text())
            self.translations.append((widget.setAccessibleName, en, ja))
            widget.setFixedHeight(36)
            if isinstance(widget, QLineEdit):
                widget.setStyleSheet("padding: 4px 10px;")
            (advanced_form if widget in (self.model, self.voice) else form).addRow(label, widget)
        config = QWidget()
        config.setLayout(form)
        setup_layout.addWidget(config)
        self.config = setup
        options = self.button("Voice settings ▾", "音声の詳細設定 ▾", lambda: None)
        options.setCheckable(True)
        options.toggled.connect(advanced.setVisible)
        setup_layout.addWidget(options, 0, Qt.AlignLeft)
        keys = QHBoxLayout()
        keys.addWidget(self.remember, 1)
        keys.addWidget(self.forget)
        advanced_layout.addLayout(keys)
        advanced_layout.addWidget(self.refresh, 0, Qt.AlignLeft)
        advanced.hide()
        setup_layout.addWidget(advanced)
        self.hands_free = QCheckBox(self.tr("Hands-free · use headphones", "ハンズフリー · ヘッドホン推奨"))
        self.translations.append((self.hands_free.setText, "Hands-free · use headphones", "ハンズフリー · ヘッドホン推奨"))
        setup_layout.addWidget(self.hands_free)
        self.label("Live voice sends audio and typed prompts to this provider and uses API billing. Subscription-agent sign-in does not include voice API access. Nothing is sent until you start.",
            "音声会話では音声と入力内容を選択した提供者に送信し、API の利用料金がかかります。エージェントのサブスク認証とは別です。開始するまで送信しません。", setup_layout)
        layout.addWidget(setup)
        self.status = self.label("Ready when you are", "いつでも始められます", layout)
        self.status.setStyleSheet("color:#a9d5c1")
        controls = QHBoxLayout()
        self.start = self.button("Start conversation", "会話を開始", self.start_call)
        self.start.setObjectName("primary")
        self.end = self.button("End", "終了", self.stop)
        self.end.setEnabled(False)
        controls.addWidget(self.start, 1)
        controls.addWidget(self.end)
        layout.addLayout(controls)
        self.mic = QPushButton()
        self.mic.setMinimumHeight(44)
        self.mic.setEnabled(False)
        self.mic.pressed.connect(self.mic_pressed)
        self.mic.released.connect(self.mic_released)
        layout.addWidget(self.mic)
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setTextVisible(False)
        self.meter.setFixedHeight(4)
        self.meter.setAccessibleName(self.tr("Microphone level", "マイク音量"))
        layout.addWidget(self.meter)
        self.interrupt = self.button("Stop audio", "音声を止める", self.interrupt_reply)
        self.interrupt.setEnabled(False)
        layout.addWidget(self.interrupt, 0, Qt.AlignRight)
        self.transcript = QPlainTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.tr("Your conversation appears here. Audio is not saved.", "会話がここに表示されます。音声は保存しません。"))
        self.translations.append((self.transcript.setPlaceholderText, "Your conversation appears here. Audio is not saved.", "会話がここに表示されます。音声は保存しません。"))
        self.transcript.setMinimumHeight(150)
        layout.addWidget(self.transcript, 1)
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText(self.tr("Add a prompt to this conversation…", "この会話にメッセージを追加…"))
        self.translations.append((self.prompt.setPlaceholderText, "Add a prompt to this conversation…", "この会話にメッセージを追加…"))
        self.prompt.setFixedHeight(76)
        layout.addWidget(self.prompt)
        actions = QHBoxLayout()
        self.send = self.button("Send prompt", "メッセージを送信", self.send_text)
        self.send.setEnabled(False)
        self.handoff = self.button("Review in chat ↗", "確認してチャットへ ↗", self.review_in_chat)
        actions.addWidget(self.send)
        actions.addWidget(self.handoff)
        layout.addLayout(actions)
        self.provider.currentIndexChanged.connect(self.provider_changed)
        self.hands_free.toggled.connect(self.mic_label)
        self.provider_changed()
        self.refresh_microphones()
        self.mic_label()

    def set_locale(self):
        for setter, en, ja in self.translations:
            setter(self.tr(en, ja))
        self.mic_label()
        self.render_transcript()

    def provider_changed(self):
        identity = self.provider.currentData()
        provider = PROVIDERS[identity]
        self.model.setText(provider.model)
        self.voice.clear()
        self.voice.addItems(provider.voices)
        self.key.clear()
        self.remember.setChecked(False)
        self.owner.preferences.setValue("live/provider", identity)
        self.status.setText(self.tr("Uses a saved voice key or ", "保存した音声キー、または環境変数を使用: ") + provider.key_env)

    def refresh_microphones(self):
        previous = self.microphones.currentData()
        self.microphones.clear()
        for source in sources():
            if source.kind == "microphone":
                self.microphones.addItem(source.label, source.device)
        index = self.microphones.findData(previous)
        if index >= 0:
            self.microphones.setCurrentIndex(index)

    def key_name(self):
        return "live/keys/" + self.provider.currentData()

    def forget_key(self):
        self.owner.preferences.remove(self.key_name())
        self.owner.preferences.sync()
        self.key.clear()
        self.status.setText(self.tr("Saved voice key removed.", "保存した音声キーを削除しました。"))

    def resolve_key(self):
        key = self.key.text().strip()
        if key:
            if self.remember.isChecked():
                self.owner.preferences.setValue(self.key_name(), base64.b64encode(protect(key.encode())).decode("ascii"))
                self.owner.preferences.sync()
            return key
        saved = self.owner.preferences.value(self.key_name(), "")
        if saved:
            return protect(base64.b64decode(saved, validate=True), decrypt=True).decode()
        provider = PROVIDERS[self.provider.currentData()]
        return os.environ.get(provider.key_env, "").strip()

    def start_call(self):
        owner = self.owner
        if self.session is not None or owner.job is not None or owner.stream is not None or owner.meeting_active:
            return
        if owner.global_dictation.enabled:
            self.status.setText(self.tr("Turn off global dictation before starting live voice.", "音声会話を始める前にグローバル音声入力をオフにしてください。"))
            return
        try:
            key = self.resolve_key()
            if not key:
                self.status.setText(self.tr("Enter a voice API key first.", "音声 API キーを入力してください。"))
                self.key.setFocus()
                return
            protocol = VoiceProtocol(self.provider.currentData(), self.model.text().strip(), self.voice.currentText(), self.language.currentData(), self.hands_free.isChecked())
        except (ValueError, OSError):
            self.status.setText(self.tr("Check the voice model and key. Re-enter the key if Windows cannot unlock it.", "モデルとキーを確認してください。保存したキーを読み込めない場合は再入力してください。"))
            return
        self.failed = False
        self.conversation_provider = self.provider.currentText()
        self.messages = {}
        self.render_transcript()
        self.elapsed = 0
        owner.tts.stop()
        self.session = LiveVoice(protocol, key, self.microphones.currentData(), self)
        self.session.event.connect(self.receive)
        self.session.finished.connect(self.finished)
        owner.busy(True)
        self.config.hide()
        for widget in (self.start, self.remember, self.forget, self.refresh, self.hands_free):
            widget.setEnabled(False)
        self.end.setEnabled(True)
        self.status.setText(self.tr("Connecting securely…", "安全に接続しています…"))
        self.session.start()
        self.timer.start()

    def stop(self):
        if self.session is not None:
            self.session.stop()
            self.mic.setEnabled(False)
            self.send.setEnabled(False)
            self.interrupt.setEnabled(False)
            self.end.setEnabled(False)
            self.status.setText(self.tr("Ending conversation…", "会話を終了しています…"))

    def finished(self):
        session = self.session
        self.session = None
        self.timer.stop()
        self.meter.setValue(0)
        self.owner.busy(False)
        self.config.show()
        for widget in (self.start, self.forget, self.refresh, self.hands_free):
            widget.setEnabled(True)
        self.remember.setEnabled(sys.platform == "win32")
        self.end.setEnabled(False)
        self.mic.setEnabled(False)
        self.send.setEnabled(False)
        self.interrupt.setEnabled(False)
        self.mic_label()
        if not self.failed:
            self.status.setText(self.tr("Conversation ended. Review or copy your transcript below.", "会話が終了しました。下の内容を確認・コピーできます。"))
        session.deleteLater()

    def receive(self, kind, value):
        if kind == "ready":
            self.mic.setEnabled(True)
            self.send.setEnabled(True)
            self.interrupt.setEnabled(True)
            self.status.setText(self.tr("Connected · microphone off", "接続しました · マイクはオフ"))
        elif kind == "transcript":
            identity, role, text, replace = value
            identity = str(identity)
            previous = self.messages.get(identity, (role, ""))[1]
            self.messages[identity] = (role, (text if replace else previous + text)[:20000])
            if len(self.messages) > 200:
                self.messages.pop(next(iter(self.messages)))
            self.render_transcript()
        elif kind == "error":
            self.failed = True
            errors = {
                "auth": ("Voice access was denied. Check the API key and model access.", "音声 API へのアクセスが拒否されました。キーとモデルの権限を確認してください。"),
                "limit": ("Provider limit reached. Check API quota or billing, then start again.", "提供者の利用上限に達しました。上限・請求設定を確認して再接続してください。"),
                "device": ("Could not open the microphone or speakers. Choose another microphone and check Windows audio settings.", "マイクまたはスピーカーを開けません。別のマイクと Windows の音声設定を確認してください。"),
                "backlog": ("Audio could not keep up. Conversation ended; check your connection or audio device.", "音声の処理が追いつかないため終了しました。接続と音声デバイスを確認してください。"),
                "provider": ("Provider rejected the voice request. Check your model ID, API access and quota.", "音声リクエストが拒否されました。モデル ID・API の権限・利用上限を確認してください。"),
            }
            self.status.setText(self.tr(*errors.get(value, ("Connection ended. Check your network, then start a new conversation. Nothing is resent automatically.", "接続が終了しました。ネットワークを確認して再接続してください。自動再送はしません。"))))
        elif kind == "notice":
            self.status.setText(self.tr("The provider reports a session limit or unavailable transcription. End and start again if needed.", "提供者から会話の制限、または文字起こし不可の通知がありました。必要に応じて再接続してください。"))

    def mic_label(self):
        active = bool(self.session and self.session.capture)
        text = self.tr("Mute microphone", "マイクをオフ") if active else self.tr("Unmute microphone", "マイクをオン")
        if not self.hands_free.isChecked():
            text = self.tr("Listening… release to send", "録音中…離すと送信") if active else self.tr("Hold to talk", "押している間、話す")
        self.mic.setText(text)
        self.mic.setStyleSheet("background:#254b3d;color:#d9f9e8;border:1px solid #76bba0" if active else "")

    def mic_pressed(self):
        if self.session:
            self.session.microphone(not self.session.capture if self.hands_free.isChecked() else True)
            self.mic_label()

    def interrupt_reply(self):
        if self.session:
            played = self.session.playback.clear()
            self.session.enqueue("interrupt", played)

    def mic_released(self):
        if self.session and not self.hands_free.isChecked():
            self.session.microphone(False)
            self.mic_label()

    def tick(self):
        if self.session:
            self.meter.setValue(self.session.level)
            self.elapsed += 1
            # A bounded call keeps unattended paid sessions from lasting indefinitely.
            if self.elapsed >= 30 * 60 * 10:
                self.stop()
            if not self.failed and self.session.ready.is_set() and not self.session.stopping.is_set():
                seconds = self.elapsed // 10
                state = self.tr("Microphone on", "マイクはオン") if self.session.capture else self.tr("Microphone off", "マイクはオフ")
                self.status.setText(f"{seconds // 60:02}:{seconds % 60:02} · {state} · {self.provider.currentText()}")

    def send_text(self):
        text = self.prompt.toPlainText().strip()
        if not text or not self.session or not self.session.ready.is_set():
            return
        if len(text) > 12000:
            self.status.setText(self.tr("Keep each prompt under 12,000 characters.", "メッセージは 12,000 文字以内にしてください。"))
            return
        if self.session.capture and not self.hands_free.isChecked():
            return
        if self.session.enqueue("text", text):
            self.messages["typed-" + uuid.uuid4().hex] = ("user", text)
            if len(self.messages) > 200:
                self.messages.pop(next(iter(self.messages)))
            self.prompt.clear()
            self.render_transcript()

    def render_transcript(self):
        self.transcript.setPlainText("\n\n".join((self.tr("You", "あなた") if role == "user" else self.conversation_provider or self.provider.currentText()) + "\n" + text for role, text in self.messages.values()))
        bar = self.transcript.verticalScrollBar()
        bar.setValue(bar.maximum())

    def review_in_chat(self):
        text = self.transcript.textCursor().selectedText().replace("\u2029", "\n") or self.transcript.toPlainText()
        if text:
            # Existing handoff fills the coding chat draft; it does not submit it.
            self.owner.draft_handoff.emit(text)

    def hideEvent(self, event):
        self.stop()
        super().hideEvent(event)
