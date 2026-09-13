"""Capture the real embedded Windows surface; does not launch an agent turn.

Run with --output in an ignored folder after installing windows-capture in the
verification environment. Screenshots can show locally detected account labels.
"""
import argparse
from pathlib import Path
import sys
import tempfile
import threading

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from kotoba.fleet_workspace import FleetWorkspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Windows compositor verification requires Windows.')
    from windows_capture import WindowsCapture
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix='kotoba-display-', ignore_cleanup_errors=True) as home:
        widget = FleetWorkspace(Path(home))
        if args.runtime:
            widget.runtime.root = args.runtime.resolve()
        widget.setWindowTitle('Kotoba Studio display verification')
        widget.setAttribute(Qt.WA_ShowWithoutActivating)
        widget.resize(1200, 800)
        controls = []
        checks = {}
        captures = {}
        completed = threading.Event()
        phase = ['home']
        failed = [False]

        def finish():
            widget.shutdown()
            # Closing the owned capture target ends any pending WGC session.
            # Joining its callback thread here would block Qt's close messages.
            widget.close()
            app.quit()

        def capture():
            name = phase[0]
            completed.clear()
            recorder = WindowsCapture(window_hwnd=int(widget.winId()), cursor_capture=False, draw_border=False)
            @recorder.event
            def on_frame_arrived(frame, control):
                # A Qt/PrintWindow grab omits foreign Chromium surfaces. WGC reads
                # the composed window, and this region excludes Kotoba's toolbar.
                region = frame.frame_buffer[120:-60, 40:-40, :3]
                chrome = frame.frame_buffer[100:220, 70:250, :3]
                if not chrome.size or chrome.std() <= 8:
                    return  # Wait for Chromium, not Qt's stale startup backing store.
                checks[name] = bool(region.size and region.std() > 12)
                captures[name] = frame.frame_buffer.copy()
                frame.save_as_image(str(args.output / (name + '.png')))
                completed.set()
                control.stop()
            @recorder.event
            def on_closed():
                pass
            controls.append(recorder.start_free_threaded())

        def navigated(accepted):
            checks['accounts_acknowledged'] = accepted is True
            QTimer.singleShot(600, capture)

        def advance():
            if not completed.is_set():
                return
            completed.clear()
            if phase[0] == 'home':
                phase[0] = 'accounts'
                widget.runtime.request('navigate', 'accounts', navigated)
            elif phase[0] == 'accounts':
                phase[0] = 'resized'
                widget.resize(1040, 720)
                QTimer.singleShot(600, capture)
            elif phase[0] == 'resized':
                phase[0] = 'restored'
                widget.hide()
                QTimer.singleShot(250, widget.show)
                QTimer.singleShot(1000, capture)
            else:
                a, b = captures.get('home'), captures.get('accounts')
                checks['account_page_changed'] = a is not None and b is not None and a.shape == b.shape and abs(a.astype(float) - b.astype(float)).mean() > 2
                finish()

        def ready(_):
            QTimer.singleShot(1800, capture)

        widget.runtime.ready.connect(ready)
        timer = QTimer(widget)
        timer.timeout.connect(advance)
        timer.start(100)
        deadline = QTimer(widget)
        deadline.setSingleShot(True)
        deadline.timeout.connect(lambda: (failed.__setitem__(0, True), finish()))
        deadline.start(90000)
        widget.show()
        widget.runtime.start()
        app.exec()
        timer.stop()
        deadline.stop()
        for name, passed in checks.items():
            print(f'{name}: {"PASS" if passed else "FAIL"}')
        return 0 if not failed[0] and len(checks) == 6 and all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
