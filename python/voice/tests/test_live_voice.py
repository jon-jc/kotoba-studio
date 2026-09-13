"""Native voice wire contracts and bounded audio lifecycle without paid API calls."""

import asyncio
import base64
import json
import time
from types import SimpleNamespace

import pytest

from kotoba.live_protocol import PROVIDERS, VoiceProtocol
from kotoba.live_voice import LiveVoice, Playback


def protocol(provider="openai", **kwargs):
    choice = PROVIDERS[provider]
    return VoiceProtocol(provider, choice.model, choice.voices[0], **kwargs)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_native_configuration_audio_and_text_share_session(provider):
    wire = protocol(provider, language="ja")
    setup = wire.setup()
    if provider == "google":
        assert setup["setup"]["generationConfig"]["responseModalities"] == ["AUDIO"]
        assert setup["setup"]["realtimeInputConfig"]["automaticActivityDetection"]["disabled"]
        assert wire.text("日本語の指示") == [{"realtimeInput": {"activityStart": {}}}, {"realtimeInput": {"text": "日本語の指示"}}, {"realtimeInput": {"activityEnd": {}}}]
        assert wire.begin() == [{"realtimeInput": {"activityStart": {}}}]
        assert wire.end() == [{"realtimeInput": {"activityEnd": {}}}]
        assert wire.input_rate == 16000
    else:
        session = setup["session"]
        vad = session["audio"]["input"]["turn_detection"] if provider == "openai" else session["turn_detection"]
        assert vad is None
        assert wire.text("日本語の指示")[-1] == {"type": "response.create"}
        assert wire.end(False) == [{"type": "input_audio_buffer.clear"}]
        assert wire.end(True) == [{"type": "input_audio_buffer.commit"}, {"type": "response.create"}]
    assert "tools" not in json.dumps(setup)
    audio = wire.audio(b"\x01\x00" * 320)
    encoded = audio["realtimeInput"]["audio"]["data"] if provider == "google" else audio["audio"]
    assert base64.b64decode(encoded) == b"\x01\x00" * 320
    assert "Japanese" in json.dumps(setup)


def test_realtime_transcripts_replace_final_without_duplicate_and_audio_is_decoded():
    wire = protocol()
    assert wire.receive({"type": "session.created"}) == []
    assert wire.receive({"type": "session.updated"}) == [("ready", None)]
    assert wire.receive({"type": "response.output_audio_transcript.delta", "item_id": "a", "delta": "Hello"}) == [("transcript", ("a", "assistant", "Hello", False))]
    assert wire.receive({"type": "response.output_audio_transcript.done", "item_id": "a", "transcript": "Hello."}) == [("transcript", ("a", "assistant", "Hello.", True))]
    assert wire.receive({"type": "conversation.item.input_audio_transcription.completed", "item_id": "u", "transcript": "こんにちは"}) == [("transcript", ("u", "user", "こんにちは", True))]
    assert wire.receive({"type": "response.audio.delta", "delta": "AQI=", "item_id": "a"}) == [("audio", (b"\x01\x02", "a", 0))]
    assert wire.receive({"type": "error", "error": {"message": "SECRET URL", "code": "invalid"}}) == [("error", "provider")]
    assert wire.interrupt(True, "a", 0, 50) == [{"type": "response.cancel"}, {"type": "conversation.item.truncate", "item_id": "a", "content_index": 0, "audio_end_ms": 50}]


def test_gemini_interruption_transcripts_and_turn_boundaries():
    wire = protocol("google")
    assert wire.receive({"setupComplete": {}}) == [("ready", None)]
    events = wire.receive({"serverContent": {"interrupted": True, "inputTranscription": {"text": "はい"}, "outputTranscription": {"text": "承知しました"}, "turnComplete": True}})
    assert events == [("interrupt", None), ("transcript", ("user-0", "user", "はい", False)), ("transcript", ("assistant-0", "assistant", "承知しました", False)), ("done", None)]
    assert wire.receive({"serverContent": {"inputTranscription": {"text": "次"}}})[0][1][0] == "user-1"


@pytest.mark.parametrize("provider", PROVIDERS)
def test_credentials_cannot_change_destination(provider):
    wire = protocol(provider)
    url, headers = wire.connection("key&host=evil.invalid")
    assert "evil.invalid" not in url.split("/")[2]
    if provider == "google":
        assert "%26host%3D" in url
    else:
        assert headers == {"Authorization": "Bearer key&host=evil.invalid"}
    with pytest.raises(ValueError):
        VoiceProtocol(provider, "model?key=secret", PROVIDERS[provider].voices[0])


def test_playback_interrupt_discards_pending_frames_and_bounds_backlog():
    playback = Playback()
    playback.append(b"\x01\x00" * 2400, "item", 0)
    out = bytearray(4800)
    playback.callback(out, 2400, None, None)
    assert out == b"\x01\x00" * 2400
    assert playback.clear() == ("item", 0, 60)
    playback.callback(out, 2400, None, None)
    assert out == bytes(4800)
    with pytest.raises(BufferError):
        playback.append(bytes(24000 * 2 * 31))
    with pytest.raises(ValueError):
        playback.append(b"x")


def test_microphone_never_queues_audio_before_ready_or_when_muted():
    worker = LiveVoice(protocol(), "test")
    worker.microphone(True)
    worker.audio_input(b"\x01\x00" * 480, 480, None, SimpleNamespace(input_overflow=False))
    assert worker.commands.empty()
    worker.ready.set()
    worker.microphone(True)
    for _ in range(6):
        worker.audio_input(b"\x01\x00" * 480, 480, None, SimpleNamespace(input_overflow=False))
    worker.microphone(False)
    commands = list(worker.commands.queue)
    assert commands[0] == ("begin", False)
    assert commands[-1] == ("end", True)
    assert len(commands) == 8
    worker.audio_input(b"\x01\x00" * 480, 480, None, SimpleNamespace(input_overflow=False))
    assert worker.commands.qsize() == 8
    worker.stop()
    assert not worker.enqueue("text", "never replay")


def test_transport_waits_for_configuration_and_releases_both_audio_streams(monkeypatch):
    from kotoba import live_voice
    incoming = []
    opened = []
    worker = LiveVoice(protocol(), "private-key")

    class Stream:
        def __init__(self, kind, **kwargs):
            self.kind = kind
        def __enter__(self):
            opened.append(self.kind)
            return self
        def __exit__(self, *args):
            opened.remove(self.kind)

    class Socket:
        def __init__(self):
            self.events = asyncio.Queue()
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            incoming.append("closed")
        async def send(self, raw):
            event = json.loads(raw)
            incoming.append(event)
            if event["type"] == "session.update":
                assert not opened and not worker.ready.is_set()
                await self.events.put(json.dumps({"type": "session.updated"}))
            elif event["type"] == "response.create":
                worker.stop()
        async def recv(self):
            return await self.events.get()

    def connection(url, **kwargs):
        assert url.startswith("wss://api.openai.com/")
        assert kwargs["proxy"] is None and kwargs["open_timeout"] == 10
        assert kwargs["additional_headers"]["Authorization"] == "Bearer private-key"
        return Socket()

    monkeypatch.setattr(live_voice, "connect", connection)
    monkeypatch.setattr(live_voice, "device_settings", lambda *args: None)
    monkeypatch.setattr(live_voice.sd, "RawInputStream", lambda **kw: Stream("input", **kw))
    monkeypatch.setattr(live_voice.sd, "RawOutputStream", lambda **kw: Stream("output", **kw))

    async def exercise():
        session = asyncio.create_task(worker.conversation())
        try:
            deadline = time.monotonic() + 2
            while not worker.ready.is_set() and time.monotonic() < deadline:
                await asyncio.sleep(.01)
            assert worker.ready.is_set() and set(opened) == {"input", "output"}
            assert not worker.capture
            worker.enqueue("text", "Plan the change")
            await asyncio.wait_for(session, 2)
        finally:
            worker.stop()
            session.cancel()
            await asyncio.gather(session, return_exceptions=True)
    asyncio.run(exercise())
    assert opened == [] and incoming[-1] == "closed"
    assert [e["type"] for e in incoming if isinstance(e, dict)] == ["session.update", "conversation.item.create", "response.create"]


def test_transport_failure_does_not_expose_credentials(monkeypatch):
    worker = LiveVoice(protocol(), "private-key")
    events = []
    worker.event.connect(lambda kind, value: events.append((kind, value)))
    async def fail():
        raise RuntimeError("private-key in wss://secret")
    monkeypatch.setattr(worker, "conversation", fail)
    worker.run()
    assert worker.key == ""
    assert events == [("error", "connection")]


def test_end_cancels_a_stalled_connection_without_waiting_for_setup_timeout(monkeypatch):
    import threading
    worker = LiveVoice(protocol(), "private-key")
    entered = threading.Event()
    released = threading.Event()
    async def stalled():
        entered.set()
        try:
            await asyncio.sleep(60)
        finally:
            released.set()
    monkeypatch.setattr(worker, "conversation", stalled)
    worker.start()
    try:
        assert entered.wait(2)
        worker.stop()
        assert worker.wait(2000)
        assert released.is_set() and worker.key == ""
    finally:
        worker.stop()
        assert worker.wait(2000)
