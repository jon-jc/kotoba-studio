"""Windows global dictation; native paste adapted from OpenWhispr (MIT).

Source: resources/windows-fast-paste.c at c6a871db1b8ada646eb728d3592431ecc8c17723.
Unlike the upstream fallback, refuse delivery when the target loses focus.
"""

import ctypes
from ctypes import wintypes as w
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel


class KeyboardInput(ctypes.Structure):
    _fields_ = [("vk", w.WORD), ("scan", w.WORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("extra", ctypes.c_size_t)]


class MouseInput(ctypes.Structure):
    _fields_ = [("x", w.LONG), ("y", w.LONG), ("data", w.DWORD),
                ("flags", w.DWORD), ("time", w.DWORD), ("extra", ctypes.c_size_t)]


class InputUnion(ctypes.Union):
    _fields_ = [("keyboard", KeyboardInput), ("mouse", MouseInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", w.DWORD), ("value", InputUnion)]


class WindowsInput:
    def __init__(self):
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.api.GetForegroundWindow.restype = w.HWND
        self.api.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        self.api.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        self.api.SendInput.argtypes = [w.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.api.RegisterHotKey.argtypes = [w.HWND, ctypes.c_int, w.UINT, w.UINT]
        self.api.UnregisterHotKey.argtypes = [w.HWND, ctypes.c_int]

    def target(self):
        hwnd = self.api.GetForegroundWindow()
        pid = w.DWORD()
        self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return (hwnd, pid.value)

    def paste(self, target):
        if not target or not target[0] or self.target() != target:
            raise RuntimeError("Target changed; text is available in Voice Studio. / 入力先が変わりました。音声スタジオで確認してください。")
        # Never release keys physically held by the user; wait until hotkey release.
        if any(self.api.GetAsyncKeyState(key) & 0x8000 for key in (0x10, 0x11, 0x12, 0x5B, 0x5C)):
            raise RuntimeError("Release shortcut keys before pasting. / ショートカットキーを離してください。")
        name = ctypes.create_unicode_buffer(256)
        self.api.GetClassNameW(target[0], name, 256)
        terminal = name.value in {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS", "mintty",
            "VirtualConsoleClass", "PuTTY", "Alacritty", "org.wezfurlong.wezterm", "Hyper", "TMobaXterm", "kitty"}
        keys = [0x11, 0x10, 0x56] if terminal else [0x11, 0x56]
        events = [Input(1, InputUnion(keyboard=KeyboardInput(key, 0, flag, 0, 0)))
                  for flag, group in ((0, keys), (2, reversed(keys))) for key in group]
        packet = (Input * len(events))(*events)
        if self.api.SendInput(len(events), packet, ctypes.sizeof(Input)) != len(events):
            # Ensure partial insertion cannot leave our synthesized modifiers down.
            releases = (Input * len(keys))(*(Input(1, InputUnion(keyboard=KeyboardInput(k, 0, 2, 0, 0))) for k in reversed(keys)))
            self.api.SendInput(len(keys), releases, ctypes.sizeof(Input))
            raise RuntimeError("Windows blocked paste. Copy from Voice Studio. / Windows が貼り付けを拒否しました。")


class GlobalDictation(QAbstractNativeEventFilter):
    HOTKEY_ID = 0x4B53

    def __init__(self, voice):
        super().__init__()
        self.voice = voice
        self.native = WindowsInput() if sys.platform == "win32" else None
        self.enabled = False
        self.target = None
        self.overlay = QLabel()
        self.overlay.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus)
        self.overlay.setAttribute(Qt.WA_ShowWithoutActivating)
        self.overlay.setStyleSheet("background:#24272b;color:#d9f3e5;border:1px solid #579881;border-radius:16px;padding:16px;font-size:14px;")
        QApplication.instance().installNativeEventFilter(self)
        self.hide_timer = QTimer(self.overlay)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.overlay.hide)

    def set_enabled(self, enabled):
        if enabled == self.enabled:
            return
        if enabled:
            if self.native is None or not self.native.api.RegisterHotKey(None, self.HOTKEY_ID, 0x4000 | 2 | 4, 0x20):
                raise RuntimeError("Ctrl+Shift+Space is unavailable. / Ctrl+Shift+Space を登録できません。")
        elif self.native:
            self.native.api.UnregisterHotKey(None, self.HOTKEY_ID)
        self.enabled = enabled

    def notice(self, en, ja, persistent=False):
        self.hide_timer.stop()
        self.overlay.setText(en if self.voice.locale == "en" else ja)
        self.overlay.adjustSize()
        geometry = QApplication.primaryScreen().availableGeometry()
        self.overlay.move(geometry.center().x() - self.overlay.width() // 2, geometry.bottom() - self.overlay.height() - 32)
        self.overlay.show()
        if not persistent:
            self.hide_timer.start(5000)

    def nativeEventFilter(self, event_type, message):
        if self.enabled:
            msg = w.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.HOTKEY_ID:
                QTimer.singleShot(0, self.toggle)
                return True, 0
        return False, 0

    def toggle(self):
        if not self.enabled:
            return
        voice = self.voice
        if voice.job is not None or getattr(voice, "meeting_active", False):
            self.notice("Voice is busy", "音声処理中です")
            return
        if voice.stream is not None:
            if self.target:
                self.notice("Transcribing…", "文字起こし中…", True)
                voice.record()
            return
        source = voice.audio_source.currentData()
        if not source or source.kind != "microphone":
            self.notice("Select a microphone for dictation", "音声入力にはマイクを選択してください")
            return
        self.target = self.native.target()
        voice.record()
        if voice.stream is not None:
            self.notice("Listening · Ctrl+Shift+Space to finish", "録音中 · Ctrl+Shift+Space で終了", True)
        elif voice.job is None:
            self.target = None
        else:
            self.notice("Preparing speech model…", "音声モデルを準備中…", True)

    def deliver(self, transcript):
        target, self.target = self.target, None
        if not target:
            return
        if not transcript.text or transcript.review_reasons:
            self.notice("Review the transcript in Voice Studio", "音声スタジオで文字起こしを確認してください")
            return
        try:
            if self.native.target() != target:
                raise RuntimeError("Target changed")
            # Leave the transcript on the clipboard: restoring on a timer races
            # asynchronous paste in other applications (OpenWhispr clipboard.js).
            QApplication.clipboard().setText(transcript.text)
            self.native.paste(target)
            self.notice("Dictation pasted · also copied", "文字起こしを貼り付け・コピーしました")
        except RuntimeError:
            self.notice("Paste paused · review in Voice Studio", "貼り付けを保留 · 音声スタジオで確認")

    def close(self):
        self.set_enabled(False)
        QApplication.instance().removeNativeEventFilter(self)
        self.hide_timer.stop()
        self.overlay.close()
