"""Local meeting journal and bounded capture/transcription lifecycle.

Adapts OpenWhispr meetingRecordingSession.ts (session ownership),
meetingTranscriptPersistence.ts (persist before stop completes), and
meetingTranscriptionRouting.js (explicit local/cloud routing), MIT.
Upstream revision c6a871db1b8ada646eb728d3592431ecc8c17723.
"""

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import sys
import threading
from time import monotonic
import uuid

import numpy as np
from .audio_sources import LoopbackStream

SCHEMA_VERSION = 1


class MeetingStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("Meeting database requires a newer Kotoba Studio")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, created TEXT NOT NULL,
                    status TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', owner_pid INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY, meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                    start REAL NOT NULL, end REAL NOT NULL, source TEXT NOT NULL, text TEXT NOT NULL,
                    model TEXT NOT NULL, review TEXT NOT NULL, highlight INTEGER NOT NULL DEFAULT 0);
                CREATE INDEX IF NOT EXISTS segments_meeting ON segments(meeting_id, start);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, title):
        identity = str(uuid.uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO meetings(id,title,created,status,owner_pid) VALUES(?,?,?,?,?)",
                       (identity, title.strip() or "Meeting / 会議", datetime.now(timezone.utc).isoformat(), "recording", os.getpid()))
        return identity

    def append(self, identity, offset, source, transcript):
        with self.connect() as db:
            for segment in transcript.segments:
                db.execute("INSERT INTO segments(meeting_id,start,end,source,text,model,review) VALUES(?,?,?,?,?,?,?)",
                           (identity, offset + segment.start, offset + segment.end, source,
                            segment.text, transcript.model, json.dumps(transcript.review_reasons)))

    def finish(self, identity, error=""):
        with self.connect() as db:
            db.execute("UPDATE meetings SET status=?,error=? WHERE id=?", ("incomplete" if error else "complete", error, identity))

    def recover(self, alive=None):
        alive = alive or process_alive
        with self.connect() as db:
            for row in db.execute("SELECT id,owner_pid FROM meetings WHERE status='recording'").fetchall():
                if not alive(row['owner_pid']):
                    db.execute("UPDATE meetings SET status='interrupted',error='Capture interrupted; completed segments recovered.' WHERE id=?", (row['id'],))

    def search(self, query=""):
        # instr is literal substring search, including Japanese; no LIKE wildcards.
        with self.connect() as db:
            return [dict(row) for row in db.execute("""SELECT * FROM meetings m WHERE ?='' OR
                instr(lower(title),lower(?)) OR instr(lower(notes),lower(?)) OR EXISTS
                (SELECT 1 FROM segments s WHERE s.meeting_id=m.id AND instr(lower(s.text),lower(?)))
                ORDER BY created DESC""", (query, query, query, query))]

    def read(self, identity):
        with self.connect() as db:
            meeting = db.execute("SELECT * FROM meetings WHERE id=?", (identity,)).fetchone()
            if meeting is None:
                raise ValueError("Meeting no longer exists")
            return dict(meeting), [dict(row) for row in db.execute("SELECT * FROM segments WHERE meeting_id=? ORDER BY start,id", (identity,))]

    def notes(self, identity, text):
        with self.connect() as db:
            db.execute("UPDATE meetings SET notes=? WHERE id=?", (text, identity))

    def highlight(self, segment_id, enabled=True):
        with self.connect() as db:
            db.execute("UPDATE segments SET highlight=? WHERE id=?", (int(enabled), segment_id))

    def delete(self, identity):
        with self.connect() as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DELETE FROM meetings WHERE id=?", (identity,))

    def markdown(self, identity):
        meeting, segments = self.read(identity)
        rows = [f"# {meeting['title']}", "", f"{meeting['created']} · {meeting['status']}", "", "## Notes / メモ", "", meeting['notes'], "", "## Highlights / 重要事項", ""]
        def line(s):
            return f"[{int(s['start'])//60:02d}:{int(s['start'])%60:02d}] ({s['source']}) {s['text']}"
        rows.extend("- " + line(s) for s in segments if s['highlight'])
        rows.extend(["", "## Transcript / 文字起こし", ""])
        rows.extend(line(s) for s in segments)
        if meeting['error']:
            rows.extend(["", "Capture status: " + meeting['error']])
        return "\n".join(rows) + "\n"


IMPORTANT = re.compile(r"\b(decid(?:e|ed)|agreed|action item|deadline|blocker|follow.up|must|need to|next step)\b|決定|合意|対応|締め切り|期限|課題|次回|担当|必要", re.I)


def process_alive(pid):
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # Access denied is not proof of exit.
        try:
            return kernel.WaitForSingleObject(handle, 0) == 258
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def suggested_highlights(segments):
    """Extractive suggestions retain verbatim evidence; never invent an action."""
    return [row for row in segments if IMPORTANT.search(row["text"])]


class Chunker:
    """Prefer a quiet boundary after 10s; cap every chunk at 30s."""
    def __init__(self, submit, source, offset=0):
        self.submit, self.source, self.offset = submit, source, offset
        self.frames = []
        self.count = 0

    def feed(self, data, count, timing, status):
        if status:
            raise RuntimeError(str(status))
        samples = data[:, 0].copy()
        # Capture callbacks have small blocks; split defensively for imported fixtures.
        for start in range(0, len(samples), 1600):
            part = samples[start:start + 1600]
            self.frames.append(part)
            self.count += len(part)
            quiet = float(np.sqrt(np.mean(part * part))) < 0.002
            if self.count >= 480000 or (self.count >= 160000 and quiet):
                self.flush()

    def flush(self):
        if self.count:
            audio = np.concatenate(self.frames)
            offset = self.offset
            self.offset += self.count / 16000
            self.frames, self.count = [], 0
            self.submit((self.source, offset, audio))


class MeetingCapture:
    def __init__(self, store, engine, config, sources, title, changed, stream_factory=None):
        self.store, self.engine = store, engine
        self.config = replace(config, context="meeting", max_seconds=35)
        self.sources, self.title, self.changed = sources, title, changed
        self.stop_event = threading.Event()
        self.pending = queue.Queue(maxsize=8)
        self.error = ""
        self.identity = None
        self.stream_factory = stream_factory

    def stop(self):
        self.stop_event.set()

    def submit(self, item):
        try:
            self.pending.put_nowait(item)
        except queue.Full:
            self.error = "Transcription could not keep up. Capture stopped; queued segments are being saved. / 文字起こしが追いつかないため録音を停止しました。"
            self.stop_event.set()

    def run(self):
        # Loading is offline; downloading never occurs after recording starts.
        self.engine.prepare(self.config, allow_download=False)
        self.identity = self.store.create(self.title)
        self.changed(self.identity)
        streams, chunkers = [], []
        started = monotonic()
        try:
            for source in self.sources:
                chunker = Chunker(self.submit, source.label, monotonic() - started)
                chunkers.append(chunker)
                def callback(data, count, timing, status, owner=chunker):
                    try:
                        owner.feed(data, count, timing, status)
                    except Exception as error:
                        self.error = str(error)
                        self.stop_event.set()
                if self.stream_factory:
                    stream = self.stream_factory(source, callback)
                elif source.kind == "microphone":
                    import sounddevice as sd
                    stream = sd.InputStream(device=source.device, samplerate=16000, channels=1,
                                            dtype="float32", blocksize=1600, callback=callback)
                else:
                    stream = LoopbackStream(source, callback)
                streams.append(stream)
                stream.start()
            while not self.stop_event.is_set():
                if monotonic() - started >= 4 * 3600:
                    self.error = "Four-hour recording limit reached. / 録音上限の4時間に達しました。"
                    break
                failure = next((getattr(s, "error", "") for s in streams if getattr(s, "error", "")), "")
                if failure:
                    self.error = failure
                    break
                try:
                    self.process(self.pending.get(timeout=0.15))
                except queue.Empty:
                    continue
        except Exception as error:
            self.error = str(error)
        finally:
            for stream in streams:
                try:
                    stream.stop()
                except Exception as error:
                    self.error = self.error or str(error)
                finally:
                    try:
                        stream.close()
                    except Exception as error:
                        self.error = self.error or str(error)
            # Stop callbacks before draining. Final partial audio is processed
            # directly so a full queue cannot discard the meeting's last words.
            try:
                while not self.pending.empty():
                    self.process(self.pending.get_nowait())
                for chunker in chunkers:
                    chunker.submit = self.process
                    chunker.flush()
            except Exception as error:
                self.error = self.error or str(error)
            self.store.finish(self.identity, self.error)
            self.changed(self.identity)
        return self.identity

    def process(self, item):
        source, offset, audio = item
        result = self.engine.transcribe(audio, self.config)
        self.store.append(self.identity, offset, source, result)
        self.changed(self.identity)
