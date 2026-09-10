"""Windows process identity agrees with the installed shortcut identity."""
from pathlib import Path
import subprocess
import sys
import struct

import pytest
from kotoba.branding import APP_USER_MODEL_ID, icon_path


def test_native_icon_has_all_windows_sizes_and_matches_browser_artwork():
    path = icon_path()
    raw = path.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", raw)
    assert (reserved, kind, count) == (0, 1, 7)
    sizes = []
    for index in range(count):
        width, height, _, _, planes, depth, length, offset = struct.unpack_from("<BBBBHHII", raw, 6 + 16 * index)
        sizes.append(width or 256)
        assert width == height and planes == 1 and depth == 32
        assert raw[offset:offset + length].startswith(b"\x89PNG\r\n\x1a\n")
        assert offset + length <= len(raw)
    assert sizes == [16, 24, 32, 48, 64, 128, 256]
    root = Path(__file__).resolve().parents[3]
    assert path.with_suffix(".svg").read_text(encoding="utf-8") == (root / "apps/web/public/favicon.svg").read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform != "win32", reason="Windows taskbar identity API")
def test_windows_process_identity_matches_shortcuts():
    code = '''
import ctypes
from kotoba.branding import configure_windows_identity
configure_windows_identity()
value = ctypes.c_wchar_p()
assert ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(value)) == 0
try:
    print(value.value)
finally:
    ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(value, ctypes.c_void_p))
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            check=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.stdout.strip() == APP_USER_MODEL_ID
    installer = (Path(__file__).resolve().parents[1] / "installer.iss").read_text(encoding="utf-8")
    shortcuts = [line for line in installer.splitlines() if line.startswith('Name: "{group}') or line.startswith('Name: "{autodesktop}')]
    assert len(shortcuts) == 2
    for shortcut in shortcuts:
        assert f'AppUserModelID: "{APP_USER_MODEL_ID}"' in shortcut
        assert 'IconFilename: "{app}\\_internal\\assets\\kotoba.ico"' in shortcut
