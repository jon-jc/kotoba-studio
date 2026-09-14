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
    # SetParent already joins the adopted child's input queue to Qt's queue.
    if api.GetAncestor(api.GetForegroundWindow(), 2) != parent or api.GetAncestor(child, 2) != parent:
        return False
    api.SetFocus(child)
    return True
