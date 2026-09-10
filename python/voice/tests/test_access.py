"""Access settings write authoritative Harness policy rather than a UI-only flag."""
from types import SimpleNamespace
from time import monotonic
import pytest

from kotoba.access import AccessSettings


def test_default_writes_only_permission_and_preserves_revision(monkeypatch):
    calls = []
    class Remote:
        def __init__(self, url): pass
        def call(self, method, args):
            calls.append((method,args))
            if method == "settings/describe":
                return {"namespaces":[{"ns":"permission","value":{"defaultPreset":"workspace-write"},"revision":7}]}
            if method == "session/list":
                return {"items":[{"sessionId":"chat-1"},{"sessionId":"kotoba-owned"},{"sessionId":"child","parentSessionId":"chat-1"}]}
    monkeypatch.setattr("kotoba.access.HarnessRemote", Remote)
    service=AccessSettings("fixture")
    assert calls == []
    view=service.describe()
    assert view["sessions"] == [{"sessionId":"chat-1"}]
    service.set_default("read-only",7)
    mutation=next(args for method,args in calls if method=="settings/mutate")
    assert mutation == {"ns":"permission","expectedRevision":7,"ops":[{"op":"set","path":["defaultPreset"],"value":"read-only"}]}
    with pytest.raises(ValueError): service.set_default("approve-everything",7)


def test_failed_session_command_does_not_report_access_change(monkeypatch):
    class Remote:
        def __init__(self,url): pass
        def call(self,method,args):
            if method == "commands/execute": return {"result":{"kind":"error","text":"denied"}}
    monkeypatch.setattr("kotoba.access.HarnessRemote",Remote)
    with pytest.raises(RuntimeError): AccessSettings("fixture").session_mode("chat-1","danger-full-access")


@pytest.fixture
def dialog(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM","offscreen")
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import QUrl
    from kotoba.access_ui import AccessDialog
    app=QApplication.instance() or QApplication([])
    calls=[]
    class Service:
        def __init__(self,url): pass
        def describe(self): return {"mode":"workspace-write","revision":3,"sessions":[{"sessionId":"chat-1"}]}
        def set_default(self,mode,revision):
            calls.append((mode,revision))
            return {"mode":mode,"revision":4,"sessions":[]}
        def session_mode(self,identity,mode=None):
            calls.append((identity,mode))
            return mode or "read-only"
    monkeypatch.setattr("kotoba.access_ui.AccessSettings",Service)
    owner=QWidget()
    owner.url=QUrl("http://127.0.0.1:1")
    owner.voice=SimpleNamespace(locale="en",harness=SimpleNamespace(close=lambda:calls.append("reset-voice")))
    window=AccessDialog(owner)
    settle(window)
    yield window,calls
    settle(window)
    window.close()
    window.deleteLater()
    owner.deleteLater()
    app.processEvents()


def settle(dialog):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    deadline=monotonic()+5
    while dialog.job is not None and monotonic()<deadline:
        QApplication.processEvents()
        QTest.qWait(5)
    assert dialog.job is None


def test_full_access_needs_acknowledgment_and_resets_voice_only_after_save(dialog):
    window,calls=dialog
    window.choices[2].setChecked(True)
    assert not window.apply_button.isEnabled()
    window.save()
    assert calls == []
    window.ack.setChecked(True)
    assert window.apply_button.isEnabled()
    window.save()
    settle(window)
    assert calls == [("danger-full-access",3),"reset-voice"]
    assert window.current == "danger-full-access"


def test_existing_session_does_not_change_global_default(dialog):
    window,calls=dialog
    window.scope.setCurrentIndex(1)
    settle(window)
    assert window.current == "read-only"
    window.choices[1].setChecked(True)
    window.save()
    settle(window)
    assert calls == [("chat-1",None),("chat-1","workspace-write")]


def test_failed_default_save_keeps_current_access_and_voice_session(dialog, monkeypatch):
    window,calls=dialog
    def conflict(*args): raise RuntimeError("Settings changed; reload before saving")
    monkeypatch.setattr(window.service,"set_default",conflict)
    window.choices[0].setChecked(True)
    window.save()
    settle(window)
    assert window.current == "workspace-write"
    assert "reload" in window.status.text()
    assert "reset-voice" not in calls
