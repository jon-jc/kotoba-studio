"""Verify the packaged agent workspace without showing a window or calling a model."""

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from kotoba.fleet_workspace import FleetWorkspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, help="Runtime bundle containing manifest.json")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Native window embedding requires Windows.")
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix="kotoba-agent-smoke-", ignore_cleanup_errors=True) as directory:
        home = Path(directory)
        project = home / "project"
        project.mkdir()
        (project / "README.md").write_text("# English / 日本語\n", encoding="utf-8")
        for command in (["init", "-b", "main"], ["add", "README.md"],
                        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "Fixture"]):
            subprocess.run(["git", "-C", str(project), *command], check=True, capture_output=True)
        widget = FleetWorkspace(home)
        if args.runtime:
            widget.runtime.root = args.runtime.resolve()
        checks = {}

        def finish():
            widget.shutdown()
            app.quit()

        def draft_result(value):
            checks["unavailable_draft_rejected"] = value is False
            finish()

        def snapshot(value):
            checks["selected_project"] = isinstance(value, dict) and value.get("local") is True and Path(value.get("path", "")).resolve() == project.resolve()
            widget.runtime.request("draft", "レビュー用の下書き", draft_result)

        def added(value):
            checks["project_added"] = value is True
            widget.runtime.request("snapshot", "ja", snapshot)

        def ready(handle):
            checks["owned_native_window"] = widget.runtime.owns_window(int(handle))
            widget.runtime.request("addProject", str(project), added)

        widget.runtime.ready.connect(ready)
        deadline = QTimer(widget)
        deadline.setSingleShot(True)
        deadline.timeout.connect(finish)
        deadline.start(120000)
        widget.runtime.start()
        app.exec()
        deadline.stop()
        for name, passed in checks.items():
            print(f"{name}: {'PASS' if passed else 'FAIL'}")
        return 0 if len(checks) == 4 and all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
