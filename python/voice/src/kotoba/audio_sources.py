"""Explicit microphone and Windows process-tree audio capture."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import numpy as np


@dataclass(frozen=True)
class AudioSource:
    kind: str
    label: str
    device: int | None = None
    pid: int | None = None


def sources():
    import sounddevice as sd
    result = [AudioSource("microphone", "Default microphone / 既定のマイク")]
    try:
        hosts = sd.query_hostapis()
        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                host = hosts[device["hostapi"]]["name"]
                if sys.platform != "win32" or "WASAPI" in host:
                    result.append(AudioSource("microphone", device["name"], device=index))
    except sd.PortAudioError:
        pass
    if sys.platform == "win32":
        result.append(AudioSource("system", "All system audio / システム音声"))
        result.extend(window_sources())
    return result


def window_sources():
    """Window titles select their owning process tree, not individual browser tabs."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    rows, seen = [], set()
    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value and pid.value != os.getpid() and pid.value not in seen:
                    seen.add(pid.value)
                    rows.append(AudioSource("application", f"{title.value[:85]} · PID {pid.value}", pid=pid.value))
        return True
    user32.EnumWindows(callback_type(visit), 0)
    return sorted(rows, key=lambda row: row.label.casefold())


def helper_path():
    directory = Path(sys.executable).parent / "runtime" if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[4] / "dist-exe"
    return directory / "kotoba-audio-capture.exe"


def capture_arguments(source):
    if source.kind == "application":
        if source.pid is None or source.pid <= 0:
            raise ValueError("Select a running application.")
        target = ["--include-pid", str(source.pid)]
    elif source.kind == "system":
        target = ["--exclude-pid", str(os.getpid())]
    else:
        raise ValueError("Loopback capture requires a system or application source.")
    return [str(helper_path()), "start", "--sample-rate", "16000", *target]


class LoopbackStream:
    """Bounded PCM reader using OpenWhispr's native WASAPI implementation."""
    def __init__(self, source, callback):
        self.source, self.callback = source, callback
        self.process = None
        self.error = ""
        self.ready = threading.Event()
        self.readers = []

    def start(self):
        self.process = subprocess.Popen(capture_arguments(self.source), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        def events():
            for line in self.process.stderr:
                try:
                    event = json.loads(line)
                    if event.get("type") == "start":
                        self.ready.set()
                    elif event.get("type") == "error":
                        self.error = event.get("message", "Audio capture failed")
                        self.ready.set()
                except (ValueError, UnicodeError):
                    continue
        def pcm():
            remaining = 16000 * 60 * 2
            while remaining:
                data = self.process.stdout.read(min(3200, remaining))
                if not data:
                    break
                remaining -= len(data)
                samples = np.frombuffer(data[:len(data) // 2 * 2], dtype="<i2").astype(np.float32) / 32768
                self.callback(samples[:, None], len(samples), None, "")
        self.readers = [threading.Thread(target=events, daemon=True), threading.Thread(target=pcm, daemon=True)]
        for reader in self.readers:
            reader.start()
        if not self.ready.wait(6) or self.error:
            self.close()
            raise RuntimeError(self.error or "Audio capture did not become ready. Check Windows audio support.")

    def stop(self):
        if self.process is None:
            return
        self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)
        for reader in self.readers:
            reader.join(timeout=1)
        if self.process.returncode and not self.error:
            self.error = "Audio capture stopped unexpectedly. Refresh and select the application again."

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.stop()
            for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
                pipe.close()
