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
