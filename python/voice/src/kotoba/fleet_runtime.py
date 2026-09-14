"""Own Kotoba's isolated Orca runtime without exposing it to the network."""

import json
import os
from pathlib import Path
import secrets
import sys
from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal
from PySide6.QtNetwork import QLocalServer


def fleet_location():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "runtime" / "fleet"
    return Path(__file__).resolve().parents[4] / "dist-exe" / "fleet"


def launch_spec(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported agent runtime bundle")
    paths = []
    for key in ("executable", "entry"):
        path = (root / manifest[key]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Agent runtime bundle is incomplete")
        paths.append(path)
    return paths


def runtime_environment(home):
    environment = {key: value for key, value in os.environ.items()
                   if not any(part in key.upper() for part in ("API_KEY", "ACCESS_TOKEN", "AUTH_TOKEN", "SECRET", "PASSWORD"))}
    environment.pop("ELECTRON_RUN_AS_NODE", None)
    environment.update(KOTOBA_FLEET_HOME=str(home), ORCA_BACKGROUND_LAUNCH="1",
                       ORCA_TELEMETRY_DISABLED="1", DO_NOT_TRACK="1")
    return environment


class FleetRuntime(QObject):
    ready = Signal(str)
    state = Signal(str)
    focus_requested = Signal()

    def __init__(self, home, parent=None, root=None):
        super().__init__(parent)
        self.home = Path(home) / "agent-workspace"
        self.root = root or fleet_location()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.errorOccurred.connect(self.process_error)
        self.process.finished.connect(self.finished)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(90000)
        self.timer.timeout.connect(self.timed_out)
        self.buffer = b""
        self.nonce = secrets.token_hex(24)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.UserAccessOption)
        self.server.newConnection.connect(self.accept_channel)
        self.channel = None
        self.address = None
        self.requests = {}
        self.next_request = 0
        self.stopping = False

    @property
    def available(self):
        try:
            launch_spec(self.root)
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def start(self):
        if self.process.state() != QProcess.NotRunning:
            return
        try:
            executable, entry = launch_spec(self.root)
            self.home.mkdir(parents=True, exist_ok=True)
            self.nonce = secrets.token_hex(24)
            environment = QProcessEnvironment()
            for key, value in runtime_environment(self.home).items():
                environment.insert(key, value)
            environment.insert("KOTOBA_FLEET_NONCE", self.nonce)
            if not self.server.isListening() and not self.server.listen("kotoba-" + self.nonce):
                raise ValueError("Cannot open the local agent channel")
            environment.insert("KOTOBA_FLEET_PIPE", self.server.fullServerName())
            self.process.setProcessEnvironment(environment)
            self.process.setWorkingDirectory(str(entry.parent))
            self.buffer, self.address, self.stopping = b"", None, False
            self.state.emit("starting")
            self.process.start(str(executable), [str(entry)])
            self.timer.start()
        except (OSError, ValueError, KeyError, TypeError):
            self.state.emit("missing")

    def read_output(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        if len(self.buffer) > 512 * 1024:
            self.buffer = self.buffer[-512 * 1024:]
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if not line.startswith(b"{"):
                continue
            try:
                value = json.loads(line)
                if not isinstance(value, dict) or value.get("kotoba") != self.nonce:
                    continue
                if value.get("kind") == "window":
                    handle = int(value["handle"])
                    if not self.owns_window(handle):
                        continue
                    self.address = str(handle)
                    self.timer.stop()
                    self.state.emit("ready")
                    self.ready.emit(str(handle))
                elif value.get("kind") == "focus":
                    if self.address and self.owns_window(int(self.address)):
                        self.focus_requested.emit()
                elif value.get("kind") == "result":
                    callback = self.requests.pop(value.get("id"), None)
                    if callback:
                        callback(value.get("value"))
            except (ValueError, TypeError, KeyError):
                continue

    def owns_window(self, handle):
        if sys.platform != "win32" or not 0 < handle < 2**64:
            return False
        import ctypes
        from ctypes import wintypes
        owner = wintypes.DWORD()
        query = ctypes.windll.user32.GetWindowThreadProcessId
        query.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        query.restype = wintypes.DWORD
        return bool(query(handle, ctypes.byref(owner))) and owner.value == self.process.processId()

    def accept_channel(self):
        connection = self.server.nextPendingConnection()
        import ctypes
        from ctypes import wintypes
        owner = wintypes.ULONG()
        query = ctypes.windll.kernel32.GetNamedPipeClientProcessId
        query.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
        query.restype = wintypes.BOOL
        if self.channel is not None or not query(int(connection.socketDescriptor()), ctypes.byref(owner)) or owner.value != self.process.processId():
            connection.abort()
            connection.deleteLater()
            return
        self.channel = connection

    def request(self, operation, value, callback=None):
        if not self.address or self.channel is None or operation not in ("snapshot", "draft", "addProject", "navigate", "present") or not isinstance(value, str) or len(value) > 64000:
            if callback:
                callback(None)
            return
        self.next_request += 1
        identity = self.next_request
        if callback:
            self.requests[identity] = callback
            QTimer.singleShot(30000, lambda: self.expire(identity))
        self.channel.write((json.dumps(dict(id=identity, operation=operation, value=value)) + "\n").encode("utf-8"))

    def expire(self, identity):
        callback = self.requests.pop(identity, None)
        if callback:
            callback(None)

    def timed_out(self):
        self.stop()
        self.state.emit("timeout")

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.finished()

    def finished(self, *_):
        self.timer.stop()
        self.address = None
        if self.channel is not None:
            self.channel.abort()
            self.channel.deleteLater()
            self.channel = None
        self.server.close()
        for identity in list(self.requests):
            self.expire(identity)
        self.state.emit("stopped" if self.stopping else "failed")

    def stop(self):
        self.timer.stop()
        self.stopping = True
        if self.process.state() == QProcess.NotRunning:
            self.server.close()
            return
        if sys.platform == "win32":
            # Terminate only this live runtime and the processes it owns.
            QProcess.execute("taskkill.exe", ["/PID", str(self.process.processId()), "/T", "/F"])
        else:
            self.process.terminate()
        if not self.process.waitForFinished(5000):
            self.process.kill()
            self.process.waitForFinished(2000)
