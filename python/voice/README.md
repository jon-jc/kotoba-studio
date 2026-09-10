# Kotoba Studio / ことば

Japanese and English voice input for the full DeepSeek Harness, built directly in this fork. The original runtime, plugins, tools, web application, and Electron desktop remain available. See [the inspection](INSPECTION.md) for integration decisions and qualification limits.

## Development

From the repository root, install the voice application and the same-checkout Python SDK into a virtual environment:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e python/voice
.venv/Scripts/python -m pip install --no-deps -e python/sdk
pnpm install --frozen-lockfile
pnpm run build
.venv/Scripts/python -m kotoba.workspace
```

The desktop finds the built checkout CLI in development and the colocated runtime executable in a Windows distribution. Configure the model API key through the environment (`DEEPSEEK_API_KEY`) or the session-only settings field. Speech recognition runs locally; the first model load downloads model weights. Reviewed prompts go to the configured Harness model provider and are persisted by Harness. Audio is not saved by microphone capture. Export is explicit.

```powershell
python -m pytest python/voice/tests
python -m kotoba.evaluate references.jsonl --output report.json
```

Reference records contain `language` (`ja`, `en`, or `mixed`), `reference`, and `hypothesis`. Scores from automatic captions must be labeled caption agreement. Model decoder scores are not accuracy percentages.

## Windows desktop

See [installation and testing](WINDOWS.md) for the installer, source build, and verification commands. Kotoba Studio embeds the original Harness web composition and adds a bilingual voice workspace, explicit microphone/system/application capture, a read-only code explorer, and a PowerShell command console. The Models and Plugins buttons open the upstream settings controls.

## Voice workflow

The top-right **English / 日本語** selector changes the native desktop and voice panels and remembers the choice on this device. It preserves the current chat, terminal, code view, transcript, speech settings, and evaluation reference. Language changes are disabled during recording or inference. The same toggle updates the embedded chat language without a reload. Core chat and model settings have Japanese translations; extension strings without Japanese entries fall back to English. Conversation content is not translated.

OpenWhispr's saved-phrase matcher is ported into the voice workflow. Open **Saved phrases**, choose **New**, enter a spoken trigger and its expansion, choose **Apply phrase**, then **Save**. Record or type the trigger and choose **Expand phrases**; the expansion is one undoable draft edit, and original ASR evidence remains in the session. Triggers match case-insensitively, longest-first, at spaces or Unicode punctuation/symbol boundaries. Japanese triggers need a pause represented by punctuation or a space: `署名。` expands, while `電子署名` does not. Replacements never recursively trigger other phrases. Phrase content is stored unencrypted in the local application-data `snippets.json`; audio and transcripts are not added to that file. Cancelling the editor discards its edits. **Copy and open chat** copies reviewed text and opens the full workspace; paste it into the chosen provider's chat and send explicitly.

## 日本語

右上の **English / 日本語** でデスクトップと音声パネルの表示言語を切り替えます。選択は端末に保存され、会話やターミナルの状態は維持されます。録音・処理中は切り替えできません。埋め込みのチャットも同時に切り替わります。日本語未対応の拡張機能の文言は英語で表示されます。会話本文は翻訳しません。

**定型文を管理 → 新規** で合図と展開文を入力し、**定型文を反映 → 保存** で確定します。文字起こし後に **定型文を展開** を押し、内容を確認してください。日本語の合図は句読点や空白で区切ります。展開は **元に戻す** で取り消せます。定型文は端末内に平文で保存されます。**コピーしてチャットを開く** を押すと、選択したモデルの会話に貼り付けて送信できます。自動送信はしません。

ことばは、DeepSeek Harness の機能を維持した日本語・英語対応の音声ワークスペースです。音声はローカルで文字起こしし、送信前に内容を確認・修正できます。初回は音声モデルのダウンロードが必要です。送信したテキストは設定済みのモデルプロバイダーへ送られ、Harness の会話履歴に保存されます。

精度を優先する候補は多言語版 `large-v3`、応答速度を比較する候補は `turbo` です。日本語は文字誤り率、英語は単語誤り率で評価します。自動字幕との一致率は、人手で検証した認識精度とは区別します。話者分離とリアルタイムの割り込みは、未検証の機能として扱います。

## Product branding

Kotoba Studio uses a generated speech-bubble and waveform mark across the native window, seven-size Windows icon, installer, browser favicon, sidebar, and conversation hero. The master artwork and README banner live in [assets/brand](../../assets/brand); [build_icon.py](build_icon.py) packages the shared mark as SVG and ICO assets. An evergreen and jade palette joins the native shell and embedded chat. Windows file properties identify Kotoba Studio. Product-facing copy uses Kotoba Studio while API provider names, runtime package identities, licenses, and upstream notices remain intact. Existing installation and application-data identifiers are preserved for upgrades.

The desktop has a compact activity rail, resizable voice dock, bottom terminal, and searchable command palette. Ctrl+K opens commands, Ctrl+Shift+V toggles voice, Ctrl+J toggles the terminal, and Ctrl+Shift+E opens files. Hiding a dock preserves its draft and output. The English / 日本語 toggle updates both shell and core chat controls.

Kotoba Studio の音声波形付き吹き出しアイコンを、アプリ、インストーラー、ブラウザー、会話画面で統一しています。表示上の製品名は Kotoba Studio です。API 提供方名、パッケージ識別子、ライセンス、上流の署名は保持します。更新時も既存の設定とデータを引き継ぎます。

## Local language models

**Local models** runs a user-selected GGUF file using the bundled, pinned llama.cpp Windows x64 CPU engine. No Python model server or Ollama installation is required for GGUF mode. Model weights are not included: choose a multilingual instruction model compatible with llama.cpp and its license. Select the file and context size, press **Start / discover**, then **Use selected model for voice and register in chat**. In the full chat composer, explicitly select **Kotoba Local**. Restart the local engine after reopening the app; model loading is never automatic.

The same page discovers models from an already-running **Ollama** (`http://127.0.0.1:11434/v1`) or **LM Studio** (`http://127.0.0.1:1234/v1`) server. Load the model there first and enter its configured context size. External server processes are not managed by Kotoba. Only loopback HTTP endpoints are accepted; model discovery ignores proxy settings and refuses redirects. Native inference uses an ephemeral authenticated loopback port, stores its credential through the existing Harness manager, and stops with the app. Registration replaces only the `kotoba-local` provider and preserves other routes.

The full SDK agent profile, session history, tool execution, and plugin architecture remain available. Native CPU performance, context capacity, Japanese/English generation, and tool reliability depend on the selected model and hardware. A small model is useful for integration smoke checks, not evidence of production accuracy. Speech recognition remains a separate local Whisper pipeline. No cloud fallback or automatic turn retry is enabled; an unavailable server or incomplete generation produces an error. Agent tools may independently access the network when used. GPU acceleration and model downloads are not managed in this release.

**ローカルモデル** で GGUF ファイルとコンテキスト長を指定し、**起動 / モデルを検出 → 音声で使用し、チャットにモデルを登録** を押します。チャット入力欄では **Kotoba Local** を選択してください。GGUF モードは同梱の CPU 推論エンジンで動作し、Ollama は不要です。モデルの重みは含まれません。Ollama / LM Studio を使用する場合は、先にそのアプリでモデルとサーバーを起動してください。アプリを再起動した後は推論エンジンを再度起動します。日本語・英語やツールの品質はモデルに依存します。モデル接続の失敗時にクラウドへ自動転送しません。

Kotoba Studio starts without the upstream Internal Testing Notice. Provider setup remains available; choose Configure later to use the Local models page.
