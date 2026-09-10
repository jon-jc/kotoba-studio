"""Explicit BYOK audio uploads; no retry, telemetry, or local/cloud fallback."""

import io
from time import perf_counter
from urllib.parse import urlsplit
import wave

import httpx
import numpy as np
from .speech import Segment, Transcript


class CloudSpeech:
    def __init__(self, endpoint, model, key, transport=None):
        url = urlsplit(endpoint)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Use an HTTPS transcription endpoint without credentials or query parameters")
        if not model.strip() or not key.strip():
            raise ValueError("Enter a speech model and API key")
        self.endpoint, self.model, self.key, self.transport = endpoint, model, key, transport

    def transcribe(self, audio, config):
        start = perf_counter()
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
        data = {"model": self.model, "response_format": "json"}
        if config.language != "auto":
            data["language"] = config.language
        if config.glossary:
            data["prompt"] = config.glossary
        try:
            with httpx.Client(timeout=90, follow_redirects=False, trust_env=False, transport=self.transport) as client:
                response = client.post(self.endpoint, headers={"Authorization": "Bearer " + self.key},
                    data=data, files={"file": ("audio.wav", buffer.getvalue(), "audio/wav")})
                if not 200 <= response.status_code < 300:
                    raise RuntimeError(f"Speech provider returned HTTP {response.status_code}. No automatic retry or fallback.")
                payload = response.json()
        except httpx.HTTPError:
            raise RuntimeError("Speech provider connection failed. No automatic retry or fallback.") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ValueError("Speech provider returned an invalid transcript")
        text = payload["text"].strip()
        duration = len(audio) / 16000
        segments = (Segment(0, duration, text, None, None),) if text else ()
        return Transcript(text, config.language, 0, segments, duration, perf_counter() - start,
                          "cloud:" + self.model, () if text else ("no_speech",))
