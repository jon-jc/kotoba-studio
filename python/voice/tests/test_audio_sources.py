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


def test_loopback_reader_continues_past_one_minute_and_closes_pipes(monkeypatch):
    import io
    import threading
    from kotoba.audio_sources import LoopbackStream
    complete = threading.Event()
    samples = []
    class Process:
        stdin = io.BytesIO()
        stdout = io.BytesIO(bytes(16000 * 65 * 2))
        stderr = io.BytesIO(b'{"type":"start"}\n')
        returncode = 0
        def wait(self, timeout): return 0
        def poll(self): return 0
    process = Process()
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr("subprocess.CREATE_NO_WINDOW", 0, raising=False)
    def callback(data, count, timing, status):
        samples.append(count)
        if sum(samples) >= 16000 * 65:
            complete.set()
    stream = LoopbackStream(AudioSource("system", "fixture"), callback)
    stream.start()
    try:
        assert complete.wait(5)
    finally:
        stream.stop()
        stream.close()
    assert sum(samples) == 16000 * 65
    assert all(not reader.is_alive() for reader in stream.readers)
    assert all(pipe.closed for pipe in (process.stdin, process.stdout, process.stderr))
