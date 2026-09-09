"""Capture scope must remain explicit and separate from all-system loopback."""

import os
import pytest
from kotoba.audio_sources import AudioSource, capture_arguments


def test_application_capture_includes_only_selected_process_tree():
    args = capture_arguments(AudioSource("application", "Meeting", pid=321))
    assert args[1:] == ["start", "--sample-rate", "16000", "--include-pid", "321"]
    assert "--exclude-pid" not in args


def test_system_capture_excludes_own_process_tree():
    args = capture_arguments(AudioSource("system", "System"))
    assert args[-2:] == ["--exclude-pid", str(os.getpid())]


@pytest.mark.parametrize("source", [AudioSource("application", "Gone"), AudioSource("application", "Invalid", pid=0), AudioSource("microphone", "Mic")])
def test_invalid_selection_does_not_fall_back_to_system(source):
    with pytest.raises(ValueError):
        capture_arguments(source)
