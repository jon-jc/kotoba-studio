"""Owned background gateway: explicit start/stop, durable delivery, signed LINE ingress."""

import socket
import threading
import time
from contextlib import contextmanager
from PySide6.QtCore import QObject, QThread, Signal, QLockFile
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from .messaging_adapters import PlatformAdapter, MessagingError, line_events


def line_app(store, configs, secrets):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.post("/line/{identity}")
    async def receive(identity: str, request: Request):
        config = configs.get(identity)
        if config is None:
            raise HTTPException(404)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024 * 1024:
                raise HTTPException(413)
        try:
            rows = line_events(bytes(raw), request.headers.get("x-line-signature", ""), config, secrets[identity]["secret"])
        except PermissionError:
            raise HTTPException(401) from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise HTTPException(400) from None
        store.ingest(identity, rows)
        return {"ok": True}
    return app


class LineReceiver:
    def __init__(self, app, port):
        self.socket = socket.socket()
        try:
            self.socket.bind(("127.0.0.1", port))
            self.socket.listen(128)
        except BaseException:
            self.socket.close()
            raise
        self.port = self.socket.getsockname()[1]
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_config=None, access_log=False, log_level="critical", timeout_graceful_shutdown=5)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, kwargs={"sockets": [self.socket]}, name="kotoba-line", daemon=False)
        self.thread.start()
        deadline = time.monotonic() + 8
        while not self.server.started and self.thread.is_alive() and time.monotonic() < deadline:
            time.sleep(.01)
        if not self.server.started:
            self.close()
            raise ValueError("LINE listener could not start")

    def close(self):
        self.server.should_exit = True
        self.thread.join(timeout=8)
        if self.thread.is_alive():
            self.server.force_exit = True
            self.thread.join()
        self.socket.close()


class GatewayWorker(QThread):
    status = Signal(str, str)

    def __init__(self, store, configs, port, adapter_factory=PlatformAdapter):
        super().__init__()
        self.store, self.configs, self.port = store, configs, port
        self.adapter_factory = adapter_factory
        self.stop_event = threading.Event()
        self.wake = threading.Event()
        self.ready = frozenset()

    def request_stop(self):
        self.stop_event.set()
        self.wake.set()

    def run(self):
        adapters, secrets, receiver = {}, {}, None
        try:
            for config in self.configs:
                if self.stop_event.is_set():
                    break
                identity = config["id"]
                self.status.emit(identity, "Connecting / 接続中")
                try:
                    secrets[identity] = self.store.credentials(identity)
                    adapter = self.adapter_factory(config, secrets[identity])
                    adapters[identity] = adapter
                    name = adapter.verify()
                    self.status.emit(identity, "Connected / 接続済み · " + name)
                except MessagingError as error:
                    self.status.emit(identity, str(error))
                    if identity in adapters:
                        adapters.pop(identity).close()
            lines = {c["id"]: c for c in self.configs if c["platform"] == "line" and c["id"] in adapters}
            if lines and not self.stop_event.is_set():
                try:
                    receiver = LineReceiver(line_app(self.store, lines, secrets), self.port)
                    for identity in lines:
                        self.status.emit(identity, f"LINE listening on 127.0.0.1:{receiver.port} · Verify your public HTTPS webhook / 公開 HTTPS Webhook を確認")
                except (OSError, ValueError):
                    for identity in lines:
                        self.status.emit(identity, "LINE listener failed. Check the local port. / LINE の待受に失敗しました。ポートを確認してください。")
                        adapters.pop(identity).close()
            self.ready = frozenset(adapters)
            next_poll = {identity: 0.0 for identity in adapters}
            backoff = {identity: 0.0 for identity in adapters}
            while adapters and not self.stop_event.is_set():
                for identity, adapter in adapters.items():
                    if self.stop_event.is_set():
                        break
                    now = time.monotonic()
                    if now < backoff[identity]:
                        continue
                    try:
                        for row in self.store.queued(identity):
                            if self.stop_event.is_set():
                                break
                            self.store.settle(row["id"], "sending")
                            try:
                                adapter.send(row)
                            except MessagingError as error:
                                self.store.settle(row["id"], "uncertain" if error.uncertain else "failed", str(error))
                                raise
                            except Exception:
                                self.store.settle(row["id"], "uncertain", "Interrupted response. Check the platform before sending again.")
                                raise
                            self.store.settle(row["id"], "sent")
                        if now >= next_poll[identity] and adapter.platform != "line":
                            rows, cursor = adapter.poll(self.store.cursor(identity))
                            self.store.ingest(identity, rows, cursor)
                            next_poll[identity] = time.monotonic() + (65 if adapter.platform == "slack" else 2 if adapter.platform == "telegram" else 5)
                            self.status.emit(identity, "Connected · inbox synchronized / 接続済み · 受信を同期しました")
                    except MessagingError as error:
                        backoff[identity] = time.monotonic() + error.retry_after
                        self.status.emit(identity, str(error))
                self.wake.wait(.3)
                self.wake.clear()
        except Exception:
            self.status.emit("", "Gateway stopped after a local error. Check storage and restart. / ローカルのエラーで停止しました。保存先を確認してください。")
        finally:
            self.ready = frozenset()
            if receiver is not None:
                receiver.close()
            for adapter in adapters.values():
                adapter.close()
            self.store.recover()


class MessagingGateway(QObject):
    changed = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store, self.worker = store, None
        self.states = {}
        self.pending_ai = {}
        self.lock = QLockFile(str(store.path) + ".gateway.lock")
        self.lock.setStaleLockTime(0)

    @property
    def running(self):
        return self.worker is not None

    def start(self, port=8768):
        if self.running:
            return
        if not self.lock.tryLock(0):
            raise ValueError("Another Kotoba window owns this gateway / 別の Kotoba がゲートウェイを実行中です")
        try:
            configs = [c for c in self.store.configs() if c["enabled"]]
            if not configs:
                raise ValueError("Enable at least one saved connection / 保存済みの接続を有効にしてください")
            self.store.recover()
            self.states.clear()
            self.worker = GatewayWorker(self.store, configs, port)
            self.worker.status.connect(self.update_state)
            self.worker.finished.connect(self.finished)
            self.worker.start()
        except BaseException:
            self.worker = None
            self.lock.unlock()
            raise
        self.changed.emit()

    @contextmanager
    def editing(self):
        if self.running or not self.lock.tryLock(0):
            raise ValueError("Stop the gateway in every Kotoba window before editing connections. / すべての Kotoba でゲートウェイを停止してください。")
        try:
            yield
        finally:
            self.lock.unlock()

    def update_state(self, identity, state):
        self.states[identity] = state
        self.changed.emit()

    def stop(self):
        if self.worker:
            self.worker.request_stop()
            self.changed.emit()

    def finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.lock.unlock()
        self.changed.emit()

    def send(self, identity, conversation, text):
        if not self.worker or self.worker.stop_event.is_set() or not self.worker.isRunning():
            raise ValueError("Start the gateway before sending / 送信前にゲートウェイを開始してください")
        config = next((c for c in self.worker.configs if c["id"] == identity), None)
        if not config or identity not in self.worker.ready:
            raise ValueError("This connection is not ready. Check connection status. / 接続の状態を確認してください。")
        message_id = self.store.enqueue(identity, conversation, text)
        self.worker.wake.set()
        return message_id
