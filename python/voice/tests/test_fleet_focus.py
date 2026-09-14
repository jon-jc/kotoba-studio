"""Native focus may move only within Kotoba's foreground window."""
import ctypes
from types import SimpleNamespace
from unittest.mock import Mock

from kotoba import fleet_focus


def test_focus_never_activates_background_or_detached_windows(monkeypatch):
    api = SimpleNamespace(GetForegroundWindow=Mock(return_value=10),
                          GetAncestor=Mock(side_effect=lambda handle, _: {10: 10, 20: 10}.get(handle, handle)),
                          SetFocus=Mock(), FindWindowExW=Mock(return_value=21),
                          GetWindowThreadProcessId=Mock(return_value=2), AttachThreadInput=Mock(return_value=True))
    monkeypatch.setattr(fleet_focus, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=api, kernel32=SimpleNamespace(GetCurrentThreadId=Mock(return_value=1))), raising=False)
    assert fleet_focus.focus_owned_child(10, 20)
    api.SetFocus.assert_called_once_with(21)
    assert api.AttachThreadInput.call_args_list == [((1, 2, True),), ((1, 2, False),)]
    api.FindWindowExW.assert_called_once_with(20, None, "Chrome_RenderWidgetHostHWND", None)
    api.SetFocus.reset_mock()
    api.GetForegroundWindow.return_value = 99
    assert not fleet_focus.focus_owned_child(10, 20)
    api.GetForegroundWindow.return_value = 10
    assert not fleet_focus.focus_owned_child(10, 30)
    api.SetFocus.assert_not_called()


def test_other_platforms_do_not_call_win32(monkeypatch):
    monkeypatch.setattr(fleet_focus, "sys", SimpleNamespace(platform="darwin"))
    assert not fleet_focus.focus_owned_child(10, 20)


def test_focus_falls_back_while_renderer_is_being_created(monkeypatch):
    api = SimpleNamespace(GetForegroundWindow=Mock(return_value=10),
                          GetAncestor=Mock(return_value=10), SetFocus=Mock(),
                          FindWindowExW=Mock(return_value=None),
                          GetWindowThreadProcessId=Mock(return_value=1), AttachThreadInput=Mock())
    monkeypatch.setattr(fleet_focus, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(user32=api, kernel32=SimpleNamespace(GetCurrentThreadId=Mock(return_value=1))), raising=False)
    assert fleet_focus.focus_owned_child(10, 20)
    api.SetFocus.assert_called_once_with(20)
