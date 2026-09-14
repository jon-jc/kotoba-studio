"""Opt-in packaged Windows smoke: sidebar chat, Claude first-run terminal setup and EN/JA.

Uses a disposable profile, empty Claude credentials directory and Git fixture.
Never sends a prompt or starts sign-in, and does not type into the user's desktop.
Requires installed Codex and Claude CLIs and the pinned checkout's Playwright.
"""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import QApplication
from kotoba.fleet_workspace import FleetWorkspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This smoke uses the embedded Windows runtime.")
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix="kotoba-chat-", ignore_cleanup_errors=True) as home, ExitStack() as cleanup:
        cleanup.enter_context(patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(Path(home) / "signed-out-claude")}))
        Path(os.environ["CLAUDE_CONFIG_DIR"]).mkdir()
        widget = FleetWorkspace(Path(home))
        widget.runtime.root = args.runtime.resolve()
        widget.resize(1200, 800)
        widget.setWindowTitle("Kotoba Studio chat verification")
        worker = QProcess(widget)
        worker.setProcessChannelMode(QProcess.MergedChannels)
        result, port, pending, finished = [1], [None], [""], [False]
        original_start = widget.runtime.process.start
        widget.runtime.process.start = lambda exe, argv: original_start(exe, [*argv, "--remote-debugging-port=0"])
        original_read = widget.runtime.process.readAllStandardOutput

        def read_runtime():
            data = original_read()
            match = re.search(rb"DevTools listening on ws://127\.0\.0\.1:(\d+)", bytes(data))
            if match:
                port[0] = match.group(1).decode()
            return data

        widget.runtime.process.readAllStandardOutput = read_runtime

        def finish(code=1, *_):
            if finished[0]:
                return
            finished[0] = True
            result[0] = code
            if worker.state() != QProcess.NotRunning:
                worker.kill()
                worker.waitForFinished(1000)
            widget.shutdown()
            widget.close()
            app.quit()

        def output():
            pending[0] += bytes(worker.readAllStandardOutput()).decode("utf-8", errors="replace")
            while "\n" in pending[0]:
                line, pending[0] = pending[0].split("\n", 1)
                if line.startswith("LOCALE "):
                    widget.set_locale(line[7:].strip())
                else:
                    print(line, flush=True)

        def ready(_):
            if not port[0]:
                finish()
                return
            worker.start("node", [str(Path(__file__).with_suffix(".cjs")), str(args.checkout.resolve()),
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


if __name__ == "__main__":
    raise SystemExit(main())
