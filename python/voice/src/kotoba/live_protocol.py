"""Native audio protocols. No tools, credential logging, or implicit provider fallback."""

import base64
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class VoiceProvider:
    name: str
    model: str
    voices: tuple[str, ...]
    key_env: str
    input_rate: int = 24000


PROVIDERS = {
    "openai": VoiceProvider("OpenAI Realtime", "gpt-realtime-2.1", ("marin", "cedar", "alloy", "coral"), "OPENAI_API_KEY"),
    "google": VoiceProvider("Gemini Live", "gemini-3.1-flash-live-preview", ("Kore", "Puck", "Aoede", "Charon"), "GEMINI_API_KEY", 16000),
    "xai": VoiceProvider("Grok Voice", "grok-voice-latest", ("eve", "ara", "rex", "sal", "leo"), "XAI_API_KEY"),
}


class VoiceProtocol:
    def __init__(self, provider, model, voice, language="en", hands_free=False):
        if provider not in PROVIDERS or language not in ("en", "ja", "auto"):
            raise ValueError("Unsupported voice configuration")
        if not model or len(model) > 128 or not all(c.isalnum() or c in "-._" for c in model):
            raise ValueError("Invalid voice model ID")
        if voice not in PROVIDERS[provider].voices:
            raise ValueError("Unsupported voice")
        self.provider, self.model, self.voice = provider, model, voice
        self.language, self.hands_free = language, hands_free
        self.input_rate = PROVIDERS[provider].input_rate
        self.turn = 0

    def connection(self, key):
        if self.provider == "google":
            return ("wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=" + quote(key, safe=""), {})
        host = "api.openai.com" if self.provider == "openai" else "api.x.ai"
        return f"wss://{host}/v1/realtime?model={quote(self.model, safe='')}", {"Authorization": "Bearer " + key}

    def setup(self):
        language = {"en": "English", "ja": "Japanese", "auto": "the language the user speaks (English or Japanese)"}[self.language]
        instruction = (f"You are Kotoba Studio's voice collaborator. Respond in {language}. "
            "Be concise and natural in speech. Preserve names, code identifiers and numbers. "
            "Ask when speech is unclear. Typed prompts and speech are the same conversation. "
            "You cannot inspect files or execute actions here. Help prepare instructions the user can review and send to their coding agent.")
        if self.provider == "google":
            return {"setup": {"model": "models/" + self.model,
                "generationConfig": {"responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}}},
                "systemInstruction": {"parts": [{"text": instruction}]},
                "inputAudioTranscription": {}, "outputAudioTranscription": {},
                "realtimeInputConfig": {"automaticActivityDetection": {"disabled": not self.hands_free}}}}
        audio = {"input": {"format": {"type": "audio/pcm", "rate": 24000}},
                 "output": {"format": {"type": "audio/pcm", "rate": 24000}}}
        vad = {"type": "server_vad"} if self.hands_free else None
        session = {"instructions": instruction, "audio": audio}
        if self.provider == "openai":
            session.update(type="realtime", output_modalities=["audio"])
            audio["output"]["voice"] = self.voice
            audio["input"].update(turn_detection=vad, transcription={"model": "gpt-4o-mini-transcribe"})
            if self.language != "auto":
                audio["input"]["transcription"]["language"] = self.language
        else:
            session.update(voice=self.voice, turn_detection=vad)
            if self.language != "auto":
                audio["input"]["transcription"] = {"language_hint": self.language}
        return {"type": "session.update", "session": session}

    def audio(self, pcm):
        data = base64.b64encode(pcm).decode("ascii")
        if self.provider == "google":
            return {"realtimeInput": {"audio": {"data": data, "mimeType": "audio/pcm;rate=16000"}}}
        return {"type": "input_audio_buffer.append", "audio": data}

    def begin(self):
        return [{"realtimeInput": {"activityStart": {}}}] if self.provider == "google" else [{"type": "input_audio_buffer.clear"}]

    def end(self, enough_audio=True):
        if self.provider == "google":
            return [{"realtimeInput": {"activityEnd": {}}}]
        if not enough_audio:
            return [{"type": "input_audio_buffer.clear"}]
        return [{"type": "input_audio_buffer.commit"}, {"type": "response.create"}]

    def text(self, text):
        if self.provider == "google":
            message = {"realtimeInput": {"text": text}}
            return [message] if self.hands_free else self.begin() + [message] + self.end()
        return [{"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}}, {"type": "response.create"}]

    def interrupt(self, active, item_id, content_index, played_ms):
        if self.provider == "google":
            # begin()/text() carry Gemini's interruption signal with the next input.
            return []
        events = [{"type": "response.cancel"}] if active else []
        if item_id:
            events.append({"type": "conversation.item.truncate", "item_id": item_id,
                           "content_index": content_index, "audio_end_ms": played_ms})
        return events

    def receive(self, event):
        """Yield small normalized events; raw provider errors never reach logs or UI."""
        if not isinstance(event, dict):
            raise ValueError("Invalid voice event")
        if "error" in event or event.get("type") == "error":
            code = (event.get("error") or {}).get("code", "")
            if code == "response_cancel_not_active":
                return []
            return [("error", "provider")]
        if self.provider == "google":
            result = []
            if "setupComplete" in event:
                result.append(("ready", None))
            if "goAway" in event:
                result.append(("notice", "expiry"))
            content = event.get("serverContent", {})
            if content.get("interrupted"):
                result.append(("interrupt", None))
            for role, field in (("user", "inputTranscription"), ("assistant", "outputTranscription")):
                if content.get(field, {}).get("text"):
                    result.append(("transcript", (f"{role}-{self.turn}", role, content[field]["text"], False)))
            for part in content.get("modelTurn", {}).get("parts", []):
                blob = part.get("inlineData", {})
                if blob.get("data") and blob.get("mimeType", "").startswith("audio/pcm"):
                    result.append(("audio", (base64.b64decode(blob["data"], validate=True), "", 0)))
            if content.get("turnComplete"):
                self.turn += 1
                result.append(("done", None))
            return result
        kind = event.get("type", "")
        if kind == "session.updated":
            return [("ready", None)]
        if kind == "response.created":
            return [("responding", None)]
        if kind == "input_audio_buffer.speech_started":
            return [("interrupt", None)]
        if kind in ("response.output_audio.delta", "response.audio.delta"):
            return [("audio", (base64.b64decode(event["delta"], validate=True), event.get("item_id", ""), event.get("content_index", 0)))]
        if kind in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
            return [("transcript", (event.get("item_id", "assistant"), "assistant", event.get("delta", ""), False))]
        if kind in ("response.output_audio_transcript.done", "response.audio_transcript.done", "conversation.item.input_audio_transcription.completed"):
            role = "user" if kind.startswith("conversation") else "assistant"
            return [("transcript", (event.get("item_id", role), role, event.get("transcript", ""), True))]
        if kind == "conversation.item.input_audio_transcription.failed":
            return [("notice", "transcription")]
        if kind == "response.done":
            if event.get("response", {}).get("status") == "failed":
                return [("error", "provider")]
            return [("done", None)]
        return []
