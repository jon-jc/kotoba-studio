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
.venv/Scripts/python -m kotoba.desktop
```

The desktop finds the built checkout CLI in development and the colocated runtime executable in a Windows distribution. Configure the model API key through the environment (`DEEPSEEK_API_KEY`) or the session-only settings field. Speech recognition runs locally; the first model load downloads model weights. Reviewed prompts go to the configured Harness model provider and are persisted by Harness. Audio is not saved by microphone capture. Export is explicit.

```powershell
python -m pytest python/voice/tests
python -m kotoba.evaluate references.jsonl --output report.json
```

Reference records contain `language` (`ja`, `en`, or `mixed`), `reference`, and `hypothesis`. Scores from automatic captions must be labeled caption agreement. Model decoder scores are not accuracy percentages.

## 日本語

ことばは、DeepSeek Harness の機能を維持した日本語・英語対応の音声ワークスペースです。音声はローカルで文字起こしし、送信前に内容を確認・修正できます。初回は音声モデルのダウンロードが必要です。送信したテキストは設定済みのモデルプロバイダーへ送られ、Harness の会話履歴に保存されます。

精度を優先する候補は多言語版 `large-v3`、応答速度を比較する候補は `turbo` です。日本語は文字誤り率、英語は単語誤り率で評価します。自動字幕との一致率は、人手で検証した認識精度とは区別します。話者分離とリアルタイムの割り込みは、未検証の機能として扱います。
