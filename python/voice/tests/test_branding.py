from pathlib import Path
import struct

from kotoba.branding import icon_path


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
