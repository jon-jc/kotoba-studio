# Two upstream foundations

DeepSeek Harness is the parent repository and the complete agent runtime. `openwhispr/` is a git submodule pinned to OpenWhispr `c6a871db1b8ada646eb728d3592431ecc8c17723`. Clone this project with `git clone --recurse-submodules` or run `git submodule update --init`. OpenWhispr remains an independently buildable desktop foundation with its original license and update history.

The Python bridge in `python/voice/src/kotoba/bridge.py` connects OpenWhispr's existing self-hosted speech and voice-agent routes to local bilingual ASR and the full Harness SDK. The compact Kotoba native desktop is also available as a direct client; it does not claim to bundle the entire OpenWhispr Electron application.

## Run the integrated OpenWhispr path

1. Build the Harness checkout and install the Python voice application as described in `python/voice/README.md`.
2. Set `KOTOBA_BRIDGE_TOKEN` to a locally generated random token of at least 32 characters. Set `DEEPSEEK_API_KEY` and optionally `KOTOBA_WORKSPACE`. Run `python -m kotoba.bridge`. The bridge binds only `127.0.0.1:8765` and rejects unauthenticated requests.
3. Build or install OpenWhispr following its pinned README. Select **Self-hosted** for transcription, base URL `http://127.0.0.1:8765/v1`, model `large-v3` (or `turbo`), and the bridge token as API key. Select Japanese or English explicitly for short utterances.
4. Select **Self-hosted** for the voice assistant, the same base URL and bridge token, and `deepseek-v4-flash` as model. This endpoint executes the full Harness agent. Do not select it as a text-cleanup-only model: the Harness has tools and may act on instructions.
5. Use OpenWhispr's existing global hotkeys, dictation surface, transcript/history UI, and paste controls. Test in a disposable workspace before enabling automatic paste or agent actions.

The speech endpoint accepts multipart audio; audio is decoded locally and temporary files are removed after inference. The agent endpoint accepts text-only chat-completion requests and wraps the complete caller conversation as user-provided context in a new isolated Harness session. It does not elevate caller system messages into Harness policy. Session IDs and tool history remain in the Harness home. The SSE response is emitted after the committed result; it is not incremental token streaming. Tool schemas supplied by the frontend are not delegated to the Harness, and images are rejected by validation. Configure these routes for dictation and voice-agent use, not OpenWhispr's note/calendar tool integration.

The bridge admits one operation at a time and returns HTTP 429 while busy. An agent disconnect or failure must not trigger automatic replay, since a tool may already have executed. It is a local integration service, not an internet-facing multi-tenant API.

## Reused implementation

The dictionary-echo detector is a Python adaptation of OpenWhispr's `src/utils/dictionaryEchoFilter.js`, retaining the MIT copyright notice in `python/voice/THIRD_PARTY_LICENSES/OpenWhispr.txt`. Kotoba flags suspected dictionary echoes for review instead of silently discarding text. Its conservative cleanup preserves Japanese fillers, numbers, and bilingual terms; raw transcripts remain in the session export.

The translation manifest excludes `integrations/` because it contains independently maintained upstream documentation, and `python/voice/` because this fork's voice documentation targets English/Japanese rather than the parent's English/Chinese pairing contract. Other upstream translation checks remain active.

## 日本語

DeepSeek Harness をエージェント基盤、OpenWhispr を音声デスクトップ基盤として利用します。OpenWhispr は固定リビジョンのサブモジュールです。ローカルの Python ブリッジに接続すると、日本語・英語の文字起こしと Harness のエージェント機能を利用できます。API トークンは必須です。音声アシスタント用の接続先ではツールが実行されるため、単なる文章整形用の接続先として設定しないでください。
