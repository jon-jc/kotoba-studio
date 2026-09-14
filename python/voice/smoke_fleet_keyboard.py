"""Opt-in Windows keyboard smoke on the real Agents terminal and Codex chat.

Temporarily foregrounds an owned test window. Uses an isolated profile and Git
fixture, types a harmless shell command, and leaves the chat draft unsent.
Requires the pinned checkout's Playwright installation and an installed Codex CLI.
"""
import argparse
import ctypes
import json
from pathlib import Path
import re
import sys
import tempfile

from PySide6.QtCore import QPoint, QProcess, QTimer, Qt
from PySide6.QtWidgets import QApplication
from kotoba.fleet_workspace import FleetWorkspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runtime', type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('This smoke verifies native Windows keyboard input.')
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix='kotoba-keyboard-', ignore_cleanup_errors=True) as home:
        widget = FleetWorkspace(Path(home))
        if args.runtime:
            widget.runtime.root = args.runtime.resolve()
        widget.resize(1200, 800)
        widget.setWindowTitle('Kotoba Studio keyboard verification')
        widget.setWindowFlag(Qt.WindowStaysOnTopHint)
        worker = QProcess(widget)
        worker.setProcessChannelMode(QProcess.MergedChannels)
        result, port, pending = [1], [None], ['']
        # Port zero is allocated atomically by Chromium, only in this test launch.
        original_start = widget.runtime.process.start
        widget.runtime.process.start = lambda exe, argv: original_start(exe, [*argv, '--remote-debugging-port=0'])
        original_read = widget.runtime.process.readAllStandardOutput

        def read_runtime():
            data = original_read()
            match = re.search(rb'DevTools listening on ws://127\.0\.0\.1:(\d+)', bytes(data))
            if match:
                port[0] = match.group(1).decode()
            return data

        widget.runtime.process.readAllStandardOutput = read_runtime
        api = ctypes.windll.user32
        api.GetForegroundWindow.restype = ctypes.c_void_p
        api.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        api.GetAncestor.restype = ctypes.c_void_p
        api.SetForegroundWindow.argtypes = [ctypes.c_void_p]

        class POINT(ctypes.Structure):
            _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

        api.WindowFromPoint.argtypes = [POINT]
        api.WindowFromPoint.restype = ctypes.c_void_p
        cursor = POINT()
        api.GetCursorPos(ctypes.byref(cursor))

        def finish(code=1, *_):
            result[0] = code
            if worker.state() != QProcess.NotRunning:
                worker.kill()
                worker.waitForFinished(1000)
            widget.shutdown()
            widget.close()
            api.SetCursorPos(cursor.x, cursor.y)
            app.quit()

        def native_type(action):
            if api.GetAncestor(api.GetForegroundWindow(), 2) != int(widget.winId()):
                widget.activateWindow()
                widget.raise_()
                foreground_thread = api.GetWindowThreadProcessId(ctypes.c_void_p(api.GetForegroundWindow()), None)
                current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                attached = api.AttachThreadInput(current_thread, foreground_thread, True)
                api.SetForegroundWindow(int(widget.winId()))
                if attached:
                    api.AttachThreadInput(current_thread, foreground_thread, False)

            def click():
                from ctypes import wintypes
                rect = wintypes.RECT()
                api.GetWindowRect(ctypes.c_void_p(int(widget.runtime.address)), ctypes.byref(rect))
                # Win32 cursor coordinates are physical pixels; Qt points may be
                # scaled logical pixels on a mixed-DPI desktop.
                viewport = action['viewport']
                point = QPoint(round(rect.left + action['x'] * (rect.right - rect.left) / viewport['width']),
                               round(rect.top + action['y'] * (rect.bottom - rect.top) / viewport['height']))
                target = api.WindowFromPoint(POINT(point.x(), point.y()))
                if api.GetAncestor(target, 2) != int(widget.winId()):
                    print("Native click target is outside the owned window", flush=True)
                    finish()
                    return
                api.SetCursorPos(point.x(), point.y())
                api.mouse_event(2, 0, 0, 0, 0)
                api.mouse_event(4, 0, 0, 0, 0)

                attempts = [0]
                def keys():
                    api.GetFocus.restype = ctypes.c_void_p
                    api.IsChild.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
                    class GUIINFO(ctypes.Structure):
                        _fields_ = [('cbSize', ctypes.c_ulong), ('flags', ctypes.c_ulong),
                                    *[(name, ctypes.c_void_p) for name in ('active', 'focus', 'capture', 'menu', 'move', 'caret')],
                                    ('rect', wintypes.RECT)]
                    info = GUIINFO()
                    info.cbSize = ctypes.sizeof(info)
                    api.GetGUIThreadInfo(0, ctypes.byref(info))
                    focused = info.focus
                    adopted = int(widget.runtime.address)
                    if focused != adopted and not api.IsChild(adopted, focused):
                        attempts[0] += 1
                        if attempts[0] < 90:
                            QTimer.singleShot(33, keys)
                        else:
                            widget.grab().save(str(args.output / "native-focus-failure.png"))
                            print("Native input focus did not reach the embedded renderer", focused, adopted, flush=True)
                            finish()
                        return
                    characters = iter(action['text'])
                    def next_key():
                        if api.GetAncestor(api.GetForegroundWindow(), 2) != int(widget.winId()):
                            finish()
                            return
                        char = next(characters, None)
                        if char is None:
                            return
                        value = {'\n': 13, '\x1b': 27}.get(char)
                        if value is None:
                            value = api.VkKeyScanW(ord(char))
                        if value < 0:
                            finish()
                            return
                        scan = api.MapVirtualKeyW(value & 255, 0)
                        if value & 256:
                            api.keybd_event(16, api.MapVirtualKeyW(16, 0), 0, 0)
                        api.keybd_event(value & 255, scan, 0, 0)
                        api.keybd_event(value & 255, scan, 2, 0)
                        if value & 256:
                            api.keybd_event(16, api.MapVirtualKeyW(16, 0), 2, 0)
                        # Let native console input consume real scan-code pairs.
                        QTimer.singleShot(20, next_key)
                    next_key()
                QTimer.singleShot(300, keys)
            QTimer.singleShot(400, click)

        def output():
            data = bytes(worker.readAllStandardOutput()).decode('utf8', errors='replace')
            pending[0] += data
            while '\n' in pending[0]:
                line, pending[0] = pending[0].split('\n', 1)
                if line.startswith('NATIVE_TYPE '):
                    native_type(json.loads(line[len('NATIVE_TYPE '):]))
                elif line == 'RESTORE':
                    widget.hide()
                    QTimer.singleShot(200, widget.show)
                else:
                    print(line, flush=True)

        def ready(_):
            if not port[0]:
                finish()
                return
            worker.start('node', [str(Path(__file__).with_suffix('.cjs')), str(args.checkout.resolve()),
                                  port[0], home, str(args.output.resolve())])

        worker.readyReadStandardOutput.connect(output)
        worker.finished.connect(finish)
        widget.runtime.ready.connect(ready)
        deadline = QTimer(widget)
        deadline.setSingleShot(True)
        deadline.timeout.connect(finish)
        deadline.start(180000)
        widget.show()
        widget.runtime.start()
        app.exec()
        deadline.stop()
        return result[0]


if __name__ == '__main__':
    raise SystemExit(main())
