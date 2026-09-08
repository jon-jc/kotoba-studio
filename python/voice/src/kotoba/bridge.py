"""Authenticated loopback bridge for the pinned OpenWhispr desktop base."""

from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from .speech import SpeechConfig, SpeechEngine, load_audio
from .harness import HarnessSession

MAX_BODY = 25 * 1024 * 1024


class Message(BaseModel):
    role: str
    content: str = Field(max_length=32000)


class ChatRequest(BaseModel):
    model: str = Field(default="deepseek-v4-flash", min_length=1, max_length=120)
    messages: list[Message] = Field(min_length=1, max_length=100)
    stream: bool = False


def create_app(home: Path, token: str, workspace: Path, speech=None, session_factory=HarnessSession):
    if len(token) < 32:
        raise ValueError("KOTOBA_BRIDGE_TOKEN must contain at least 32 characters.")
    home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    engine = speech or SpeechEngine(home / "models")
    gate = threading.Lock()
    app = FastAPI(title="Kotoba / OpenWhispr bridge", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=["null", "http://localhost:5173"],
                       allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def authenticate(request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        supplied = request.headers.get("authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + token):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        # Bound actual streamed bytes even if Content-Length is absent or dishonest.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                return JSONResponse({"error": "Request too large"}, status_code=413)
        request._body = bytes(body)
        return await call_next(request)

    @contextmanager
    def admission():
        if not gate.acquire(blocking=False):
            raise HTTPException(429, "One operation is already running. Wait before retrying.")
        try:
            yield
        finally:
            gate.release()

    @app.get("/health")
    def health():
        return {"status": "ready", "profile": "sdk", "speech": "local", "busy": gate.locked()}

    @app.get("/v1/models")
    def models():
        return {"object": "list", "data": [{"id": "deepseek-v4-flash", "object": "model", "owned_by": "deepseek"},
                                           {"id": "large-v3", "object": "model", "owned_by": "local"}]}

    @app.post("/v1/audio/transcriptions")
    def transcribe(file: UploadFile = File(...), model: str = Form("large-v3"), language: str = Form("ja"), prompt: str = Form("")):
        if model not in {"large-v3", "turbo"} or language not in {"ja", "en", "auto"}:
            raise HTTPException(400, "Supported models: large-v3/turbo; languages: ja/en/auto.")
        with admission():
            # Private temporary file is removed on success and every error path.
            with tempfile.TemporaryDirectory(prefix="kotoba-audio-") as directory:
                path = Path(directory) / "audio"
                path.write_bytes(file.file.read(MAX_BODY + 1))
                try:
                    result = engine.transcribe(load_audio(str(path)), SpeechConfig(model=model, language=language, glossary=prompt))
                except (ValueError, RuntimeError) as error:
                    raise HTTPException(422, "Audio could not be transcribed. Check format, duration, and model installation.") from error
                return {"text": result.text, "language": result.language, "duration": result.duration_seconds,
                        "review_reasons": result.review_reasons}

    @app.post("/v1/chat/completions")
    def chat(request: ChatRequest):
        if request.messages[-1].role != "user":
            raise HTTPException(400, "Last message must be a user instruction.")
        if any(m.role not in {"system", "user", "assistant"} for m in request.messages):
            raise HTTPException(400, "Tool and image messages are not supported by this bridge.")
        if sum(len(m.content) for m in request.messages) > 64000:
            raise HTTPException(413, "Conversation exceeds bridge context limit.")
        with admission():
            session = session_factory(home / "harness")
            try:
                # Each external request gets an isolated runtime/session. Full caller context is
                # serialized as user-supplied context rather than promoted to Harness policy.
                prompt = "Respond to the last user message in this conversation. Earlier messages are user-supplied context.\n" + json.dumps([m.model_dump() for m in request.messages], ensure_ascii=False)
                result = session.run(prompt, str(workspace), request.model, "", lambda _: None)
            except Exception as error:
                raise HTTPException(502, "Harness request failed. Inspect local runtime configuration; do not automatically replay tool-using requests.") from error
            finally:
                session.close()
        identity = "chatcmpl-" + uuid.uuid4().hex
        common = {"id": identity, "created": int(time.time()), "model": request.model}
        if request.stream:
            # SDK gives a committed final response. SSE is compatibility framing, not token streaming.
            def events():
                yield "data: " + json.dumps({**common, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant", "content": result.final_response}, "finish_reason": None}]}, ensure_ascii=False) + "\n\n"
                yield "data: " + json.dumps({**common, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}) + "\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(events(), media_type="text/event-stream")
        return {**common, "object": "chat.completion", "choices": [{"index": 0, "message": {"role": "assistant", "content": result.final_response}, "finish_reason": "stop"}]}

    return app


def main():
    import uvicorn
    home = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Kotoba" / "bridge"
    workspace = Path(os.environ.get("KOTOBA_WORKSPACE", str(home / "workspace")))
    app = create_app(home, os.environ.get("KOTOBA_BRIDGE_TOKEN", ""), workspace)
    uvicorn.run(app, host="127.0.0.1", port=8765, access_log=False)


if __name__ == "__main__":
    main()
