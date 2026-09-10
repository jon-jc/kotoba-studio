"""Locate shared desktop artwork in source and frozen distributions."""

from pathlib import Path
import sys


def icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "kotoba.ico"
    return Path(__file__).resolve().parents[2] / "assets" / "kotoba.ico"
