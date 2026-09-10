"""Desktop-owned GGUF server and connections to existing loopback model servers."""

from pathlib import Path
import secrets
import socket
from time import monotonic

from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QNetworkProxy
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QFileDialog, QSpinBox, QFormLayout)

from .desktop import Job
from .local_models import llama_path, model_arguments, local_endpoint, discover_models, HarnessRemote


class LocalModelsPage(QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.job = None
        self.reply = None
        self.native_ready = False
        self.native_key = ""
        self.endpoint = ""
        self.diagnostics = ""
        self.labels = []
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.output)
        self.process.finished.connect(self.exited)
        self.process.errorOccurred.connect(self.process_error)
        self.network = QNetworkAccessManager(self)
        self.network.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
        self.poll = QTimer(self)
        self.poll.setInterval(500)
        self.poll.timeout.connect(self.check_ready)
        self.build()
        self.address.textChanged.connect(self.invalidate_discovery)
        self.key.textChanged.connect(self.invalidate_discovery)
        self.set_locale(owner.voice.locale)

    def tr(self, en, ja):
        return en if self.owner.voice.locale == "en" else ja

    def bind(self, widget, en, ja):
        self.labels.append((widget, en, ja))
        return widget

    def build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        title = self.bind(QLabel(), "Local models", "ローカルモデル")
        title.setStyleSheet("font-size:28px;font-weight:600")
        layout.addWidget(title)
        intro = self.bind(QLabel(), "Run a GGUF model on this PC, or connect Ollama / LM Studio. Model requests stay on loopback; agent tools can still access the network when used.",
            "GGUF モデルをこの PC で実行するか、Ollama / LM Studio に接続します。モデルへのリクエストは端末内で処理します。エージェントのツールは必要に応じてネットワークにアクセスします。")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.mode = QComboBox()
        self.mode.addItem("GGUF · CPU", "native")
        self.mode.addItem("Ollama", "ollama")
        self.mode.addItem("LM Studio", "lmstudio")
        self.mode.currentIndexChanged.connect(self.mode_changed)
        layout.addWidget(self.mode)
        file_row = QHBoxLayout()
        self.file = QLineEdit(str(self.owner.voice.preferences.value("local/model_path", "")))
        self.browse = self.bind(QPushButton(), "Choose GGUF…", "GGUF を選択…")
        self.browse.clicked.connect(self.choose)
        file_row.addWidget(self.file, 1)
        file_row.addWidget(self.browse)
        layout.addLayout(file_row)
        form = QFormLayout()
        self.address = QLineEdit("http://127.0.0.1:11434/v1")
        self.address.setEnabled(False)
        form.addRow(self.bind(QLabel(), "Local endpoint", "ローカル接続先"), self.address)
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.Password)
        self.key.setEnabled(False)
        form.addRow(self.bind(QLabel(), "Server key (optional)", "サーバーキー（任意）"), self.key)
        self.context = QSpinBox()
        self.context.setRange(1024, 131072)
        self.context.setSingleStep(1024)
        self.context.setValue(16384)
        form.addRow(self.bind(QLabel(), "Context tokens", "コンテキスト長"), self.context)
        layout.addLayout(form)
        note = self.bind(QLabel(), "Larger contexts use more RAM. For external servers, enter the context size configured there. Japanese/English quality and tool calling depend on the chosen model.",
            "長いコンテキストはメモリを多く使用します。外部サーバーでは、サーバー側の設定値を入力してください。日本語・英語の品質とツール呼び出し能力はモデルに依存します。")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        self.start = self.bind(QPushButton(), "Start / discover", "起動 / モデルを検出")
        self.start.clicked.connect(self.connect_model)
        self.stop = self.bind(QPushButton(), "Stop local engine", "ローカル推論を停止")
        self.stop.clicked.connect(self.stop_engine)
        self.stop.setEnabled(False)
        row.addWidget(self.start)
        row.addWidget(self.stop)
        layout.addLayout(row)
        self.models = QComboBox()
        layout.addWidget(self.models)
        self.use = self.bind(QPushButton(), "Use selected model for voice and register in chat", "音声で使用し、チャットにモデルを登録")
        self.use.setObjectName("primary")
        self.use.setEnabled(False)
        self.use.clicked.connect(self.register)
        layout.addWidget(self.use)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

    def set_locale(self, locale):
        for widget, en, ja in self.labels:
            widget.setText(en if locale == "en" else ja)

    def mode_changed(self):
        native = self.mode.currentData() == "native"
        self.file.setEnabled(native)
        self.browse.setEnabled(native)
        self.address.setEnabled(not native)
        self.key.setEnabled(not native)
        self.address.setText("http://127.0.0.1:11434/v1" if self.mode.currentData() == "ollama" else "http://127.0.0.1:1234/v1")
        self.models.clear()
        self.use.setEnabled(False)

    def invalidate_discovery(self):
        self.models.clear()
        self.use.setEnabled(False)

    def choose(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Choose GGUF model", "GGUF モデルを選択"), self.file.text(), "GGUF (*.gguf)")
        if path:
            self.file.setText(path)

    def controls(self, busy):
        running = self.process.state() != QProcess.NotRunning
        for widget in (self.mode, self.start, self.context):
            widget.setEnabled(not busy and not running)
        self.address.setEnabled(not busy and self.mode.currentData() != "native")
        self.key.setEnabled(not busy and self.mode.currentData() != "native")
        self.file.setEnabled(not busy and not running and self.mode.currentData() == "native")
        self.browse.setEnabled(self.file.isEnabled())
        self.use.setEnabled(not busy and self.models.count() > 0 and (not running or self.native_ready))
        self.stop.setEnabled(running and self.job is None)
        self.models.setEnabled(not busy)

    def work(self, task, done):
        if self.job is not None:
            return
        self.controls(True)
        self.job = Job(task)
        self.job.result.connect(done)
        self.job.failure.connect(self.failed)
        self.job.finished.connect(self.finished)
        self.job.start()

    def finished(self):
        job, self.job = self.job, None
        job.deleteLater()
        self.controls(False)

    def failed(self, error):
        for secret in (self.key.text(), self.native_key):
            if secret:
                error = error.replace(secret, "[redacted]")
        self.status.setText(error[:1500])

    def connect_model(self):
        self.models.clear()
        self.use.setEnabled(False)
        if self.mode.currentData() != "native":
            try:
                self.endpoint = local_endpoint(self.address.text())
            except ValueError as error:
                self.failed(str(error))
                return
            endpoint, key = self.endpoint, self.key.text()
            self.status.setText(self.tr("Discovering local models…", "ローカルモデルを検出中…"))
            self.work(lambda emit: discover_models(endpoint, key), self.discovered)
            return
        try:
            executable = llama_path()
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            args = model_arguments(Path(self.file.text()), port, self.context.value())
        except (OSError, ValueError) as error:
            self.failed(str(error))
            return
        self.native_ready = False
        self.native_key = secrets.token_urlsafe(32)
        self.endpoint = f"http://127.0.0.1:{port}/v1"
        environment = QProcessEnvironment.systemEnvironment()
        for key in environment.keys():
            if any(word in key.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD")) or key.startswith("LLAMA_"):
                environment.remove(key)
        environment.insert("LLAMA_API_KEY", self.native_key)
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(executable.parent))
        self.diagnostics = ""
        self.process.start(str(executable), args)
        self.started = monotonic()
        self.controls(True)
        self.stop.setEnabled(True)
        self.status.setText(self.tr("Loading GGUF on CPU…", "GGUF を CPU に読み込み中…"))
        self.poll.start()

    def check_ready(self):
        if monotonic() - self.started > 180:
            self.stop_engine()
            self.failed(self.tr("Model loading timed out. Try a smaller model or context.", "読み込みがタイムアウトしました。小さいモデルやコンテキストをお試しください。"))
            return
        if self.reply is not None or self.process.state() != QProcess.Running:
            return
        request = QNetworkRequest(QUrl(self.endpoint + "/models"))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.ManualRedirectPolicy)
        request.setTransferTimeout(1500)
        request.setRawHeader(b"Authorization", ("Bearer " + self.native_key).encode())
        reply = self.network.get(request)
        self.reply = reply
        def complete():
            self.reply = None
            try:
                if reply.error() == QNetworkReply.NoError and self.process.state() == QProcess.Running:
                    import json
                    data = json.loads(bytes(reply.readAll()))
                    if any(item.get("id") == "kotoba-local" for item in data.get("data", [])):
                        self.native_ready = True
                        self.poll.stop()
                        self.owner.voice.preferences.setValue("local/model_path", self.file.text())
                        self.discovered(["kotoba-local"])
                        self.controls(False)
            except (ValueError, AttributeError, TypeError):
                pass  # A startup/non-model response is retried until the bounded deadline.
            finally:
                reply.deleteLater()
        reply.finished.connect(complete)

    def discovered(self, models):
        self.models.clear()
        self.models.addItems(models)
        self.status.setText(self.tr("Model available. Register it to use voice and chat.", "モデルを検出しました。登録すると音声とチャットで使用できます。"))

    def register(self):
        if self.owner.url is None or self.owner.voice.job is not None:
            self.failed(self.tr("Wait for the runtime and current voice request.", "ランタイムと音声処理の完了をお待ちください。"))
            return
        endpoint, model, context = self.endpoint, self.models.currentText(), self.context.value()
        key = self.native_key if self.mode.currentData() == "native" else self.key.text()
        url = self.owner.url.toString()
        self.work(lambda emit: HarnessRemote(url).register_local(endpoint, model, context, key),
                  lambda provider: self.registered(provider, model))

    def registered(self, provider, model):
        self.owner.voice.harness.close()
        self.owner.voice.provider = provider
        self.owner.voice.model = model
        self.owner.voice.api_key = ""
        self.owner.voice.route_label.setText(provider + " · " + model)
        self.owner.voice.preferences.setValue("voice/provider", provider)
        self.owner.voice.preferences.setValue("voice/model", model)
        self.owner.voice.preferences.setValue("voice/model_provider", provider)
        self.owner.voice.refresh_routes()
        self.status.setText(self.tr("Voice uses this local model. In chat, choose Kotoba Local in the model selector. No cloud fallback is enabled.",
            "音声はこのローカルモデルを使用します。チャットのモデル選択で Kotoba Local を選んでください。クラウドへの自動切り替えは行いません。"))

    def output(self):
        self.diagnostics = (self.diagnostics + bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace"))[-5000:]

    def exited(self, code, status):
        self.poll.stop()
        self.native_ready = False
        self.models.clear()
        self.controls(False)
        if code:
            self.failed(self.tr("Local engine stopped: ", "ローカル推論が停止しました：") + self.diagnostics[-1500:])

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.poll.stop()
            self.controls(False)
            self.failed(self.process.errorString())

    def stop_engine(self):
        self.poll.stop()
        self.native_ready = False
        if self.reply is not None:
            self.reply.abort()
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(3000)
        self.models.clear()
        self.controls(False)
        self.status.setText(self.tr("Local engine stopped.", "ローカル推論を停止しました。"))
