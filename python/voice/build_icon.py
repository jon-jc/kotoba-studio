"""Render the generated Kotoba master artwork into a Windows icon with seven native sizes."""

from pathlib import Path
import struct
import base64

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage


def build_icon():
    assets = Path(__file__).resolve().parent / "assets"
    master = QImage(str(assets.parents[2] / "assets/brand/kotoba-mark.png"))
    if master.isNull():
        raise ValueError("Missing Kotoba master artwork")
    images = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = master.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Icon rendering failed")
        images.append((size, bytes(buffer.data())))
    raster = base64.b64encode(images[-1][1]).decode("ascii")
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><image width="256" height="256" href="data:image/png;base64,' + raster + '"/></svg>\n'
    (assets / "kotoba.svg").write_text(svg, encoding="utf-8", newline="\n")
    (assets.parents[2] / "apps/web/public/favicon.svg").write_text(svg, encoding="utf-8", newline="\n")
    offset = 6 + 16 * len(images)
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    for size, payload in images:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(payload), offset)
        offset += len(payload)
    (assets / "kotoba.ico").write_bytes(header + entries + b"".join(payload for _, payload in images))


if __name__ == "__main__":
    build_icon()
