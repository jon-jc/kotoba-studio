import threading
from dataclasses import replace
import numpy as np
import pytest
from kotoba.audio_sources import AudioSource
from kotoba.meetings import MeetingCapture, MeetingStore, Chunker, suggested_highlights
from kotoba.speech import SpeechConfig, Transcript, Segment


def transcript(text="次回は金曜日、田中さんが担当します。", duration=1):
    return Transcript(text, "ja", 1, (Segment(0, duration, text, -0.2, 0),), duration, .1, "fixture", ())


def test_saved_transcript_highlights_notes_search_and_delete(tmp_path):
    store = MeetingStore(tmp_path / "notes.sqlite3")
    identity = store.create("Release review / リリース会議")
    store.append(identity, 62, "Meeting app", transcript())
    store.notes(identity, "Check migration ownership")
    _, rows = store.read(identity)
    assert suggested_highlights(rows) == rows
    store.highlight(rows[0]['id'])
    store.finish(identity)
    reopened = MeetingStore(store.path)
    assert reopened.search("田中")[0]['id'] == identity
    assert reopened.search("ownership")[0]['id'] == identity
    assert reopened.search("%") == []
    assert "[01:02] (Meeting app) 次回は金曜日" in reopened.markdown(identity)
    reopened.delete(identity)
    assert reopened.search() == []
    with reopened.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM segments").fetchone()[0] == 0


def test_crash_recovery_preserves_committed_segments(tmp_path):
    store = MeetingStore(tmp_path / "notes.sqlite3")
    identity = store.create("Recovery")
    store.append(identity, 0, "Microphone", transcript())
    store.recover(alive=lambda pid: True)
    assert store.read(identity)[0]['status'] == "recording"
    store.recover(alive=lambda pid: False)
    meeting, rows = store.read(identity)
    assert meeting['status'] == "interrupted"
    assert len(rows) == 1


def test_chunker_bounded_and_flush_preserves_every_sample():
    chunks = []
    chunker = Chunker(chunks.append, "microphone")
    audio = np.full((16000 * 61 + 317, 1), .1, dtype=np.float32)
    chunker.feed(audio, len(audio), None, "")
    chunker.flush()
    assert [row[1] for row in chunks] == [0, 30, 60]
    assert max(len(row[2]) for row in chunks) <= 480000
    np.testing.assert_array_equal(np.concatenate([row[2] for row in chunks]), audio[:, 0])


def test_stop_waits_for_capture_quiescence_then_saves_tail(tmp_path):
    entered, release = threading.Event(), threading.Event()
    callbacks_done = threading.Event()
    class Engine:
        def prepare(self, config, allow_download):
            assert not allow_download and config.context == "meeting"
        def transcribe(self, audio, config):
            assert callbacks_done.is_set()
            return transcript(duration=len(audio) / 16000)
    class Stream:
        def __init__(self, source, callback):
            self.callback = callback
        def start(self):
            self.callback(np.ones((16000, 1), dtype=np.float32) * .1, 16000, None, "")
            entered.set()
        def stop(self):
            assert release.wait(5)
            self.callback(np.ones((8000, 1), dtype=np.float32) * .1, 8000, None, "")
            callbacks_done.set()
        def close(self):
            assert callbacks_done.is_set()
    store = MeetingStore(tmp_path / "notes.sqlite3")
    session = MeetingCapture(store, Engine(), SpeechConfig(), [AudioSource("microphone", "Me")], "Tail", lambda _: None, Stream)
    thread = threading.Thread(target=session.run)
    thread.start()
    try:
        assert entered.wait(5)
        session.stop()
        release.set()
    finally:
        release.set()
        session.stop()
        thread.join(10)
    assert not thread.is_alive()
    meeting, rows = store.read(session.identity)
    assert meeting['status'] == "complete"
    assert rows[0]['end'] - rows[0]['start'] == 1.5


def test_backpressure_stops_capture_with_explicit_incomplete_status(tmp_path):
    class Engine:
        def prepare(self, *args, **kwargs): pass
        def transcribe(self, audio, config): return transcript()
    class Stream:
        def __init__(self, source, callback): self.callback = callback
        def start(self): self.callback(np.full((16000 * 300, 1), .1, dtype=np.float32), 0, None, "")
        def stop(self): pass
        def close(self): pass
    store = MeetingStore(tmp_path / "notes.sqlite3")
    session = MeetingCapture(store, Engine(), SpeechConfig(), [AudioSource("microphone", "Me")], "Overload", lambda _: None, Stream)
    session.run()
    meeting, rows = store.read(session.identity)
    assert meeting['status'] == "incomplete"
    assert "could not keep up" in meeting['error']
    assert len(rows) == 8
