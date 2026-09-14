"""The desktop boundary validates bundles, process messages and project context."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def application(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_bundle_cannot_launch_outside_its_root(tmp_path):
    from kotoba.fleet_runtime import launch_spec
    root = tmp_path / "bundle"
    root.mkdir()
    (tmp_path / "other.exe").touch()
    (root / "app.asar").touch()
    (root / "manifest.json").write_text(json.dumps(dict(schema=1, executable="../other.exe", entry="app.asar")))
    with pytest.raises(ValueError, match="incomplete"):
        launch_spec(root)
    (root / "agent.exe").touch()
    (root / "manifest.json").write_text(json.dumps(dict(schema=1, executable="agent.exe", entry="app.asar")))
    assert launch_spec(root) == [root / "agent.exe", root / "app.asar"]


def test_overlay_does_not_confuse_an_unrelated_empty_object_for_a_patch(tmp_path):
    import importlib.util
    source = Path(__file__).resolve().parents[1] / "prepare_fleet_source.py"
    spec = importlib.util.spec_from_file_location("fleet_source_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / "defaults.ts"
    before = "export const DEFAULT_ARGS = YOLO_ARGS"
    after = "export const DEFAULT_ARGS = {}"
    target.write_text("const unrelated = {}\n" + before)
    module.replace_once(tmp_path, "defaults.ts", before, after)
    module.replace_once(tmp_path, "defaults.ts", before, after)
    assert target.read_text() == "const unrelated = {}\n" + after


def test_subscription_runtime_does_not_inherit_api_secrets(tmp_path, monkeypatch):
    from kotoba.fleet_runtime import runtime_environment
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-only")
    monkeypatch.setenv("ELECTRON_RUN_AS_NODE", "1")
    result = runtime_environment(tmp_path)
    assert "OPENAI_API_KEY" not in result and "ANTHROPIC_AUTH_TOKEN" not in result
    assert "ELECTRON_RUN_AS_NODE" not in result
    assert result["DO_NOT_TRACK"] == "1"
    assert result["KOTOBA_FLEET_HOME"] == str(tmp_path)


def test_runtime_ignores_foreign_windows_and_untrusted_messages(application, tmp_path, monkeypatch):
    from kotoba.fleet_runtime import FleetRuntime
    runtime = FleetRuntime(tmp_path, root=tmp_path)
    ready = []
    runtime.ready.connect(ready.append)
    monkeypatch.setattr(runtime, "owns_window", lambda handle: handle == 123)
    payload = b'not json\nnull\n' + b'\n'.join(json.dumps(value).encode() for value in [
        dict(kotoba="wrong", kind="window", handle="123"),
        dict(kotoba=runtime.nonce, kind="window", handle="124"),
        dict(kotoba=runtime.nonce, kind="window", handle="123"),
    ]) + b'\n'
    monkeypatch.setattr(runtime, "process", SimpleNamespace(readAllStandardOutput=lambda: payload))
    runtime.read_output()
    assert ready == ["123"]
    runtime.timer.stop()


def test_unready_runtime_rejects_drafts_without_queuing(application, tmp_path):
    from kotoba.fleet_runtime import FleetRuntime
    runtime = FleetRuntime(tmp_path, root=tmp_path)
    result = []
    runtime.request("draft", "実装してください", result.append)
    assert result == [None] and runtime.requests == {}


def test_workspace_presents_only_an_attached_visible_runtime(application, tmp_path, monkeypatch):
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    calls = []
    monkeypatch.setattr(workspace.runtime, "request", lambda *args: calls.append(args))
    monkeypatch.setattr(workspace, "isVisible", lambda: True)
    workspace.present()
    assert calls == []
    workspace.runtime.address = "123"
    workspace.container = object()
    workspace.present()
    assert calls[0][:2] == ("present", "")
    monkeypatch.setattr(workspace, "isVisible", lambda: False)
    workspace.present()
    assert len(calls) == 1
    workspace.runtime.address = None
    workspace.container = None
    workspace.deleteLater()


def test_account_navigation_reports_failure_and_waits_for_runtime(application, tmp_path, monkeypatch):
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    assert not workspace.buttons["accounts"].isEnabled()
    workspace.set_state("ready")
    assert workspace.buttons["accounts"].isEnabled()
    calls = []
    def request(operation, target, callback):
        calls.append((operation, target))
        callback(False)
    monkeypatch.setattr(workspace.runtime, "request", request)
    workspace.navigate("accounts")
    assert calls == [("navigate", "accounts")]
    assert "Could not open" in workspace.context.text()
    workspace.set_locale("ja")
    workspace.navigation_result(None)
    assert "開けません" in workspace.context.text()
    workspace.set_state("failed")
    assert not workspace.buttons["accounts"].isEnabled()
    workspace.deleteLater()


def test_present_reanchors_and_repaints_the_foreign_surface(application, tmp_path):
    from PySide6.QtCore import QRect
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    geometries = []
    workspace.container = SimpleNamespace(rect=lambda: QRect(0, 0, 1040, 680))
    workspace.foreign_window = SimpleNamespace(setGeometry=geometries.append)
    workspace.present_result(True)
    workspace.fit_surface()
    assert geometries == [QRect(0, 0, 1041, 680), QRect(0, 0, 1040, 680)]
    workspace.container = None
    workspace.foreign_window = None
    workspace.deleteLater()


def test_remote_or_missing_worktree_never_becomes_local_context(application, tmp_path):
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    changes = []
    workspace.context_changed.connect(changes.append)
    workspace.snapshot(dict(path=str(tmp_path), local=False, title="Remote task"))
    workspace.snapshot(dict(path=str(tmp_path / "missing"), local=True))
    assert changes == []
    workspace.snapshot(dict(path=str(tmp_path), local=True, title="Implementation"))
    assert changes == [str(tmp_path)]
    workspace.set_locale("ja")
    assert workspace.buttons["accounts"].text() == "エージェントのアカウント"
    workspace.draft_result(False)
    assert "保持" in workspace.context.text()
    workspace.shutdown()


def test_disconnected_workspace_clears_stale_project(application, tmp_path):
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    workspace.current_path = str(tmp_path)
    workspace.set_state("failed")
    assert workspace.current_path == "" and not workspace.timer.isActive()
    workspace.shutdown()


def test_embedded_keyboard_focus_only_follows_visible_container(application, tmp_path, monkeypatch):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QWidget
    from kotoba.fleet_workspace import FleetWorkspace
    workspace = FleetWorkspace(tmp_path)
    container = QWidget(workspace)
    workspace.container = container
    calls = []
    monkeypatch.setattr(workspace, "focus_native_window", lambda: calls.append("focus"))
    workspace.eventFilter(container, QEvent(QEvent.FocusIn))
    assert calls == []
    workspace.show()
    workspace.eventFilter(container, QEvent(QEvent.FocusIn))
    workspace.eventFilter(container, QEvent(QEvent.FocusOut))
    workspace.eventFilter(workspace, QEvent(QEvent.FocusIn))
    assert calls == ["focus"]
    workspace.container = None
    workspace.close()
    workspace.shutdown()
