# Kotoba Studio

![Kotoba Studio — Voice. Code. 日本語 / English.](assets/brand/kotoba-banner.png)

**A Japanese and English voice workspace for building with AI.**

English | [中文](README.zh.md)

[Windows setup](python/voice/WINDOWS.md) · [Local models](python/voice/README.md#local-language-models) · [Architecture](docs/architecture.md)

Kotoba Studio brings voice, conversations, code, terminal commands, and model routing into one Windows desktop application. Speak in Japanese or English, review the transcript, then choose a local model or an API provider to carry out the task. The complete DeepSeek Harness runtime powers the agent beneath the interface.

## The workspace

A compact activity rail opens chat, files, routing, plugins, and local models. A resizable voice studio sits beside your work, and the terminal opens below it. The top-right English / 日本語 selector updates the native interface and core chat controls without reloading the conversation.

| Workflow | Available now |
| --- | --- |
| Voice input | Local Whisper transcription; microphone, system audio, application process capture, and imported recordings |
| Japanese + English | Explicit or automatic speech-language selection; 507 Japanese interface translations; terminology hints and transcript review |
| Native local models | Bundled llama.cpp CPU engine for GGUF files, plus connections to Ollama and LM Studio |
| Full agent harness | Persistent conversations, tool execution, skills, subagents, workflows, agent presets, and Cordis plugins |
| Model routing | Provider endpoints, credential management, model discovery, and per-conversation selection |
| Developer workspace | File browsing, code preview, persistent PowerShell console, and the original agent tool interfaces |
| Dictation workflow | OpenWhispr-derived audio capture and saved phrases; Unicode-aware expansion, undo, and reviewed-text handoff |
| Measurable quality | Transcription latency, real-time factor, Japanese CER / English WER against a supplied reference, and agent usage statistics |

**Ctrl+K** opens the command palette. **Ctrl+Shift+V** toggles Voice Studio. **Ctrl+J** toggles the terminal. **Ctrl+Shift+E** opens the code explorer.

<a id="run"></a>

## Run on Windows

Build or install `Kotoba-Studio-0.4.0-Setup.exe`. The installer includes Python, Qt WebEngine, the matching agent runtime, capture helper, and CPU inference engine. Model weights are separate. See the [Windows guide](python/voice/WINDOWS.md) for build commands and verification.

1. Open a working folder.
2. Configure a provider in **Routing**, or choose **Configure later** and open **Local models**.
3. For native inference, choose a compatible GGUF model, start it, and register it. Select **Kotoba Local** in the chat composer.
4. In **Voice Studio**, choose a recording source, input language, and speech model.
5. Record or import audio, check names and numbers, then send the reviewed instruction.

Local-model requests stay on loopback. An unavailable local server produces an error; there is no automatic cloud fallback or turn replay. Agent tools can still access the network when used. Audio capture stays in memory, while submitted text and agent sessions are stored locally by the harness. API providers receive text you explicitly send to them.

## 日本語で使う

右上の **English / 日本語** で表示言語を切り替えます。音声スタジオで録音元・言語・音声モデルを選択し、文字起こしの名前と数字を確認してから送信してください。会話本文やコードそのものは翻訳しません。日本語未対応の拡張機能の文言は英語で表示します。

**ローカルモデル** で GGUF を選択すると、同梱の CPU エンジンで実行できます。Ollama / LM Studio への接続も可能です。登録後、チャットでは **Kotoba Local** を選びます。アプリを再起動した後は推論エンジンを再度起動してください。モデルの重みはインストーラーに含まれません。

<a id="run-from-source"></a>

## Develop

```powershell
git clone https://github.com/jon-jc/japan-ai-harness.git
cd japan-ai-harness
pnpm install --frozen-lockfile
pnpm run build:official
python -m venv .venv
.venv/Scripts/python -m pip install -e "python/voice[test]"
.venv/Scripts/python -m pip install --no-deps -e python/sdk
.venv/Scripts/python python/voice/prepare_local_runtime.py
.venv/Scripts/python -m kotoba.workspace
```

The development application uses the built checkout CLI when a packaged runtime is absent. A Windows installer requires the matching native runtime and capture helper; follow [the packaging guide](python/voice/WINDOWS.md). Run `python -m pytest python/voice/tests` for the voice application and `pnpm run test:gui` for the client interfaces. See [development](docs/development.md), [contributing](CONTRIBUTING.md), and the [integration inspection](python/voice/INSPECTION.md).

## Engineering boundaries

This is an unsigned developer preview, not a production-qualified release. Speech and agent quality depend on the model, recording, hardware, and task. Small GGUF integration tests do not establish Japanese accuracy or reliable tool use. Caption agreement is not a substitute for human-reviewed evaluation references.

Speaker diarization, streaming interruption, managed GPU inference, automatic model downloads for GGUF, and system-wide paste-at-cursor are not implemented. Existing local speech weights may require an initial network download. Extension interfaces without Japanese entries use English fallback. Review [SAFETY.md](SAFETY.md) before giving an agent access to a workspace.

## Built on open source

Kotoba Studio is a fork of [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness), retaining its actual runtime and Cordis plugin architecture. The voice workflow integrates code from [OpenWhispr](https://github.com/OpenWhispr/openwhispr). Native local inference uses [llama.cpp](https://github.com/ggml-org/llama.cpp). Upstream package identifiers and API provider names remain intact for compatibility and attribution.

[MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Bundled runtime licenses](python/voice/THIRD_PARTY_LICENSES)
