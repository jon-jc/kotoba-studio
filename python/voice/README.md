# Kotoba / ことば

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

The top-right **English / 日本語** selector changes the native desktop and voice panels and remembers the choice on this device. It preserves the current chat, terminal, code view, transcript, speech settings, and evaluation reference. Language changes are disabled during recording or inference. The embedded upstream web application retains its separate English/Chinese locale system.

OpenWhispr's saved-phrase matcher is ported into the voice workflow. Open **Saved phrases**, choose **New**, enter a spoken trigger and its expansion, choose **Apply phrase**, then **Save**. Record or type the trigger and choose **Expand phrases**; the expansion is one undoable draft edit, and original ASR evidence remains in the session. Triggers match case-insensitively, longest-first, at spaces or Unicode punctuation/symbol boundaries. Japanese triggers need a pause represented by punctuation or a space: `署名。` expands, while `電子署名` does not. Replacements never recursively trigger other phrases. Phrase content is stored unencrypted in the local application-data `snippets.json`; audio and transcripts are not added to that file. Cancelling the editor discards its edits. **Copy and open Harness chat** copies reviewed text and opens the full workspace; paste it into the chosen provider's chat and send explicitly.

## 日本語

右上の **English / 日本語** でデスクトップと音声パネルの表示言語を切り替えます。選択は端末に保存され、会話やターミナルの状態は維持されます。録音・処理中は切り替えできません。埋め込みの Harness 画面は、元の英語・中国語設定を使用します。

**定型文を管理 → 新規** で合図と展開文を入力し、**定型文を反映 → 保存** で確定します。文字起こし後に **定型文を展開** を押し、内容を確認してください。日本語の合図は句読点や空白で区切ります。展開は **元に戻す** で取り消せます。定型文は端末内に平文で保存されます。**コピーして Harness チャットを開く** を押すと、選択したモデルの会話に貼り付けて送信できます。自動送信はしません。

ことばは、DeepSeek Harness の機能を維持した日本語・英語対応の音声ワークスペースです。音声はローカルで文字起こしし、送信前に内容を確認・修正できます。初回は音声モデルのダウンロードが必要です。送信したテキストは設定済みのモデルプロバイダーへ送られ、Harness の会話履歴に保存されます。

精度を優先する候補は多言語版 `large-v3`、応答速度を比較する候補は `turbo` です。日本語は文字誤り率、英語は単語誤り率で評価します。自動字幕との一致率は、人手で検証した認識精度とは区別します。話者分離とリアルタイムの割り込みは、未検証の機能として扱います。
