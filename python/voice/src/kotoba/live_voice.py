"""Bounded desktop audio transport for an explicitly started native voice session."""

import asyncio
from contextlib import ExitStack
import json
import logging
import queue
import sys
import threading
import time

import numpy as np
from PySide6.QtCore import QThread, Signal
import sounddevice as sd
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

TRANSPORT_LOG = logging.getLogger("kotoba.live.transport")
TRANSPORT_LOG.addHandler(logging.NullHandler())
TRANSPORT_LOG.propagate = False


def device_settings(device, direction):
    if sys.platform == "win32":
        info = sd.query_devices(device, direction)
        if "WASAPI" in sd.query_hostapis(info["hostapi"])["name"]:
            return sd.WasapiSettings(auto_convert=True)
    return None


class Playback:
    """PCM16 mono at 24 kHz; discard pending audio immediately on interruption."""
    def __init__(self):
        self.lock = threading.Lock()
        self.data = bytearray()
        self.item, self.index, self.played = "", 0, 0

    def append(self, pcm, item="", index=0):
        if len(pcm) % 2:
            raise ValueError("Invalid PCM frame")
        with self.lock:
            if len(self.data) + len(pcm) > 24000 * 2 * 30:
                raise BufferError("Playback backlog")
            if item and item != self.item:
                self.item, self.index, self.played = item, index, 0
            self.data.extend(pcm)

    def callback(self, outdata, frames, timing, status):
        count = frames * 2
        with self.lock:
            size = min(count, len(self.data))
            outdata[:] = bytes(self.data[:size]) + bytes(count - size)
            del self.data[:size]
            self.played += size

    def clear(self):
        with self.lock:
            # Exclude the last output block, which may still be in the device buffer.
            result = self.item, self.index, max(0, self.played // 48 - 40)
            self.data.clear()
            self.item, self.index, self.played = "", 0, 0
            return result


class LiveVoice(QThread):
    event = Signal(str, object)

    def __init__(self, protocol, key, device=None, parent=None):
        super().__init__(parent)
        self.protocol, self.key, self.device = protocol, key, device
        self.commands = queue.Queue(maxsize=150)
        self.stopping = threading.Event()
        self.ready = threading.Event()
        self.lock = threading.Lock()
        self.capture = False
        self.captured = 0
        self.level = 0
        self.fault = ""
        self.playback = Playback()
        self.active_response = False
        self.suppress_audio = False
        self.loop = None
        self.task = None

    def enqueue(self, kind, data=None):
        if self.stopping.is_set():
            return False
        try:
            self.commands.put_nowait((kind, data))
            return True
        except queue.Full:
            self.fault = "backlog"
            self.stop()
            return False

    def microphone(self, enabled):
        if not self.ready.is_set():
            return
        with self.lock:
            if enabled == self.capture:
                return
            if not self.protocol.hands_free:
                self.enqueue("begin" if enabled else "end", self.captured >= self.protocol.input_rate // 10)
            elif not enabled and self.protocol.provider == "google":
                self.enqueue("mic_end")
            self.capture = enabled
            self.captured = 0
            self.level = 0

    def audio_input(self, data, frames, timing, status):
        with self.lock:
            if not self.capture or self.stopping.is_set():
                return
            if status.input_overflow:
                self.fault = "backlog"
                self.stopping.set()
                return
            pcm = bytes(data)
            samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
            self.level = min(100, int(np.sqrt(np.mean(samples * samples)) / 100))
            self.captured += frames
            self.enqueue("audio", pcm)

    def stop(self):
        self.stopping.set()
        self.capture = False
        self.level = 0
        self.playback.clear()
        loop, task = self.loop, self.task
        if loop is not None and task is not None:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                # The worker can finish between reading its loop and scheduling cancellation.
                pass

    async def run_session(self):
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        try:
            if not self.stopping.is_set():
                await self.conversation()
        finally:
            self.loop = self.task = None

    def run(self):
        try:
            asyncio.run(self.run_session())
        except asyncio.CancelledError:
            # Explicit End cancels even a stalled connect/send before joining the worker.
            pass
        except InvalidStatus as error:
            code = error.response.status_code
            self.event.emit("error", "auth" if code in (401, 403) else "limit" if code == 429 else "connection")
        except sd.PortAudioError:
            self.event.emit("error", "device")
        except Exception:
            # Transport exceptions may include URLs or authentication headers.
            if not self.stopping.is_set():
                self.event.emit("error", "connection")
        finally:
            self.stop()
            self.ready.clear()
            self.key = ""
            while not self.commands.empty():
                try:
                    self.commands.get_nowait()
                except queue.Empty:
                    break
            if self.fault:
                self.event.emit("error", self.fault)

    async def conversation(self):
        url, headers = self.protocol.connection(self.key)
        async with connect(url, additional_headers=headers, proxy=None, open_timeout=10,
                           close_timeout=2, max_size=2_000_000, max_queue=16,
                           ping_interval=20, ping_timeout=20, logger=TRANSPORT_LOG) as socket:
            async def send(events):
                for event in events:
                    await socket.send(json.dumps(event))

            await send([self.protocol.setup()])
            deadline = time.monotonic() + 15
            with ExitStack() as audio:
                receiver = asyncio.create_task(socket.recv())
                try:
                    while not self.stopping.is_set():
                        if not self.ready.is_set() and time.monotonic() > deadline:
                            raise TimeoutError("Voice setup timed out")
                        done, _ = await asyncio.wait([receiver], timeout=0.01)
                        if done:
                            raw = receiver.result()
                            for kind, value in self.protocol.receive(json.loads(raw)):
                                if kind == "ready" and not self.ready.is_set():
                                    audio.enter_context(sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16", blocksize=480,
                                        extra_settings=device_settings(None, "output"), callback=self.playback.callback))
                                    audio.enter_context(sd.RawInputStream(device=self.device, samplerate=self.protocol.input_rate,
                                        channels=1, dtype="int16", blocksize=self.protocol.input_rate // 50,
                                        extra_settings=device_settings(self.device, "input"), callback=self.audio_input))
                                    self.ready.set()
                                elif kind == "audio":
                                    if not self.suppress_audio:
                                        self.playback.append(*value)
                                    continue
                                elif kind == "responding":
                                    self.active_response = True
                                    self.suppress_audio = False
                                elif kind == "interrupt":
                                    item, index, played = self.playback.clear()
                                    await send(self.protocol.interrupt(False, item, index, played))
                                    self.suppress_audio = self.protocol.provider != "google"
                                elif kind == "done":
                                    self.active_response = False
                                    self.suppress_audio = False
                                elif kind == "error":
                                    self.stopping.set()
                                self.event.emit(kind, value)
                            receiver = asyncio.create_task(socket.recv())
                        # Bounded draining lets incoming audio/cancellation stay responsive.
                        for _ in range(12):
                            if self.stopping.is_set():
                                break
                            try:
                                kind, data = self.commands.get_nowait()
                            except queue.Empty:
                                break
                            if kind in ("begin", "text", "interrupt"):
                                item, index, played = data if kind == "interrupt" and data else self.playback.clear()
                                await send(self.protocol.interrupt(self.active_response, item, index, played))
                                self.active_response = False
                                self.suppress_audio = kind == "interrupt" or self.protocol.provider != "google"
                            if kind == "begin":
                                await send(self.protocol.begin())
                            elif kind == "end":
                                await send(self.protocol.end(data))
                            elif kind == "audio":
                                await send([self.protocol.audio(data)])
                            elif kind == "text":
                                await send(self.protocol.text(data))
                            elif kind == "mic_end":
                                await send([{"realtimeInput": {"audioStreamEnd": True}}])
                finally:
                    receiver.cancel()
                    await asyncio.gather(receiver, return_exceptions=True)
