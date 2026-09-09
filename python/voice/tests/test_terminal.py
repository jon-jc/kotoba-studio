"""Use the real Windows shell to verify Unicode and persistent command state."""

import subprocess
import sys

import pytest

from kotoba.terminal import powershell_arguments


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell integration")
def test_japanese_output_and_state_survive_command_boundaries(tmp_path):
    script = "$word = '日本語 English 123'\nWrite-Output $word\nWrite-Output ($word + ' 継続')\nexit\n"
    result = subprocess.run(["powershell.exe", *powershell_arguments()], input=script.encode("utf-8"),
        cwd=tmp_path, capture_output=True, timeout=15, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    lines = result.stdout.decode("utf-8").splitlines()
    assert "日本語 English 123" in lines
    assert "日本語 English 123 継続" in lines
