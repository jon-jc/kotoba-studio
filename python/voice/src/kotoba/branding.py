"""Locate shared desktop artwork in source and frozen distributions."""

from pathlib import Path
import sys

APP_USER_MODEL_ID = "KotobaStudio.Desktop"


def configure_windows_identity() -> None:
    """Separate Kotoba windows from Python's taskbar group before creating UI."""
    if sys.platform == "win32":
        import ctypes
        set_identity = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        set_identity.argtypes = [ctypes.c_wchar_p]
        set_identity.restype = ctypes.c_long
        result = set_identity(APP_USER_MODEL_ID)
        if result != 0:
            raise OSError(f"Cannot set Kotoba Studio's Windows identity: HRESULT {result:#x}")


def icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "kotoba.ico"
    return Path(__file__).resolve().parents[2] / "assets" / "kotoba.ico"
