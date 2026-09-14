"""Transfer native focus inside an already foreground, owned embedded window."""
import sys


def focus_owned_child(parent, child):
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes
    api = ctypes.windll.user32
    api.GetForegroundWindow.restype = wintypes.HWND
    api.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    api.GetAncestor.restype = wintypes.HWND
    api.SetFocus.argtypes = [wintypes.HWND]
    api.SetFocus.restype = wintypes.HWND
    # Never activate the application, another window, or a detached dialog.
    # Qt and Electron own separate UI threads; focus must cross only this
    # validated child boundary, with any temporary input attachment released.
    if api.GetAncestor(api.GetForegroundWindow(), 2) != parent or api.GetAncestor(child, 2) != parent:
        return False
    # Chromium receives text through its renderer child, not the browser frame.
    api.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    api.FindWindowExW.restype = wintypes.HWND
    renderer = api.FindWindowExW(child, None, "Chrome_RenderWidgetHostHWND", None)
    target = renderer or child
    api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    target_thread = api.GetWindowThreadProcessId(target, None)
    attached = current_thread != target_thread and api.AttachThreadInput(current_thread, target_thread, True)
    try:
        api.SetFocus(target)
    finally:
        if attached:
            api.AttachThreadInput(current_thread, target_thread, False)
    return True
