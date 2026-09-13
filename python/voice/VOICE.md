# Voice, meetings, and notes

Kotoba Studio adapts [OpenWhispr](https://github.com/OpenWhispr/openwhispr)'s Windows capture, dictation, model registry, and meeting lifecycle patterns to its Python desktop. The complete Harness remains available for reviewed agent instructions. The [upstream documentation](https://docs.openwhispr.com/) is a reference for OpenWhispr; it is not a list of features shipped by Kotoba.

## Native voice conversations

Open **Voice → Live conversation** to speak and type in the same provider session. This is a native speech-to-speech connection; local dictation remains a separate tab. Choose OpenAI Realtime, Gemini Live, or Grok Voice, a conversation language, and a microphone. **Voice settings** contains the voice and editable model ID. Defaults are `gpt-realtime-2.1`, `gemini-3.1-flash-live-preview`, and `grok-voice-latest`; model availability depends on your provider account.

Enter that provider's API key, or use `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `XAI_API_KEY` in the desktop launch environment. These voice credentials are separate from the Harness credential manager and subscription-agent accounts. **Remember key** encrypts a voice key for the current Windows user; **Forget saved key** removes it. Other platforms support session-only keys and environment variables. A supplied key overrides the saved voice key, which overrides the environment. Keys are never included in transcripts or handoffs.

Press **Start conversation**, then **Hold to talk**. Release to send the spoken turn. Use **Send prompt** to add typed instructions to the same conversation and receive a spoken reply. **Hands-free** uses the provider's speech detection; the microphone starts muted and must be explicitly unmuted. Use headphones because this desktop audio path does not implement acoustic echo cancellation. Speaking again interrupts the prior reply. **Stop audio** clears playback; OpenAI and Grok also receive cancellation and a played-duration truncation. Gemini's Stop audio is playback-only, so generation and billing may continue until that turn ends. **End** closes the connection. Closing the panel or app also ends live voice; it does not continue invisibly in the tray.

Live voice sends captured audio and typed prompts to the selected provider and incurs that provider's API charges. It does not require downloaded speech weights and never silently switches providers. Connections have bounded setup timeouts, audio queues, and a 30-minute app limit. Disconnects require an explicit new start; previous prompts and audio are not resent. Audio is held only in memory. Up to 200 transcript entries remain in the panel until a new conversation or app exit. Transcripts may be incomplete when the provider cannot transcribe a turn.

Select transcript text and choose **Review in chat**, or leave the selection empty to transfer the visible conversation. This fills the available coding-chat draft without submitting it. The voice model has no file or command tools; coding actions continue through the selected agent's permissions and review workflow. Providers without a supported native voice adapter can still use reviewed local dictation and the existing reply read-aloud option.

Protocol references: [OpenAI Realtime](https://developers.openai.com/api/docs/guides/realtime-conversations), [Gemini Live](https://ai.google.dev/gemini-api/docs/live-api/capabilities), and [Grok Voice](https://docs.x.ai/developers/rest-api-reference/inference/voice). Keyless tests cover wire messages, interruption, audio bounds, shutdown, credentials, and the native UI. Live account entitlements, paid turns, acoustic quality, and broad microphone compatibility still require testing with your provider and device.

### 音声と文字で、同じ AI と会話する

**音声 → 音声会話** で OpenAI Realtime、Gemini Live、Grok Voice を選び、日本語・英語・自動切替とマイクを設定します。**音声の詳細設定** では声とモデル ID を選べます。音声 API キーは Harness の保存済みキーやエージェントのサブスク認証とは別に設定します。環境変数も利用でき、Windows ではキーをユーザー単位で暗号化して保存・削除できます。

**会話を開始** してから **押している間、話す** を押し、離すと送信します。文字で入力したメッセージも同じ会話に加わり、音声で返答します。ハンズフリーはマイクをオンにすると提供者が発話を検出します。エコー除去は未実装のためヘッドホンを推奨します。**音声を止める** は再生を停止します。OpenAI と Grok には返答の中止も通知しますが、Gemini は再生のみの停止で、生成・課金が続く場合があります。**終了**、パネルを閉じる、アプリを閉じる操作で接続を終了します。

音声・入力内容を選択した提供者に送信し、API の利用料金がかかります。ローカルの音声モデルのダウンロードは不要です。音声は保存せず、最大 200 件の会話テキストをパネルに保持します。会話は最大 30 分で、自動再接続・再送信はしません。テキストを選択して **確認してチャットへ** を押すと、コーディング用チャットの下書きに追加します。選択しない場合は表示中の会話を追加します。自動送信・ファイル操作・コマンド実行は行いません。実際の API の利用権限、音声品質、マイクの互換性は利用者の環境で確認してください。

## Choose a speech model

In Voice Studio, choose the input language, expand **Audio settings**, and choose **Download / warm model**. Downloads are explicit. Recording and transcription only load existing local weights; missing weights produce an error. Setup displays download progress, received size when available, unpacking, and model loading. Unknown download sizes use an indeterminate bar; older Hugging Face versions may report file counts. Completion appears only after the model loads successfully. No audio is sent during a model download. Hugging Face telemetry is disabled.

| Input language | Recommended default | Other choices |
| --- | --- | --- |
| English | NVIDIA Parakeet Unified EN 0.6B, int8 CPU | Parakeet TDT v3, Whisper large-v3, Turbo, small, base |
| Japanese | Kotoba Technologies' Kotoba-Whisper v2.0, int8 CPU | Whisper large-v3, Turbo, small, base |
| Auto / mixed Japanese-English | Whisper Turbo | Other multilingual Whisper sizes |

Kotoba Technologies is an independent model publisher, not affiliated with Kotoba Studio. Its official CTranslate2 conversion runs without downloading executable model code. Japanese decoding uses 15-second windows and segment timestamps; the distilled model's incompatible word-alignment path is disabled. Parakeet does not expose calibrated confidence scores through this integration. Selected-language models are not automatic language detectors.

The [Japanese model evaluation](https://huggingface.co/kotoba-tech/kotoba-whisper-v2.0) shows dataset-dependent tradeoffs with large-v3. No model is universally best. Parakeet's English default follows [OpenWhispr's registry](https://github.com/OpenWhispr/openwhispr/blob/c6a871db1b8ada646eb728d3592431ecc8c17723/src/models/modelRegistryData.json); its archive is verified against a pinned SHA-256 before installation. Japanese and Whisper weights use the upstream Hugging Face cache. Model files are stored in the application-data `models` directory, separately from the installer.

Use a modern x64 CPU and start with 16 GB RAM for the recommended models. These are practical starting points, not a tested minimum hardware specification. Model memory competes with your coding agent and other applications. Smaller Whisper models trade accuracy for lower resource use. Parakeet runs on CPU; CUDA for Whisper requires a compatible separately installed NVIDIA runtime. The installer includes both speech engines, without a Python setup step.

## Voice setup and agent selection

Kotoba opens Chat with Voice Studio and the terminal hidden. Open Voice Studio when needed. Input language is saved separately from interface language. Recording, audio import, and meeting start check the selected model before capturing audio. Missing weights open a **Download model** / **Cancel** prompt. Download transfers model files, not your audio. After preparation, start recording again; the setup dialog clears any pending desktop paste target. Local inference never enables network downloads or cloud fallback by itself.

The Agent tab and voice Settings share the live Harness provider catalog with Chat. Choose a provider and model, or type a custom model ID for a configured provider. Add providers and saved API keys in **Chat Settings → Models**, then **Refresh models**. Unconfigured providers have no selectable model until configured. Changing providers clears the session-only key and selects that provider's model; a DeepSeek model is not carried into a local route. Voice uses the same full SDK agent runtime and saved provider credentials. A session-only key overrides only the selected route's credential reference.

音声入力・音声ファイルの読み込み・会議録音の前に、選択したモデルを確認します。未準備の場合は **モデルをダウンロード** / **キャンセル** を表示します。ダウンロードするのはモデルのファイルであり、音声は送信しません。完了後に録音を開始してください。入力言語は表示言語とは別に保存されます。起動時はチャットのみ表示します。エージェントの接続先・モデルはチャットと同じ一覧を使用します。チャット設定で接続先と API キーを追加し、音声画面で一覧を更新してください。

## Dictate at your cursor

1. Prepare the selected local model and select a microphone.
2. Enable **Desktop dictation** in Voice Studio.
3. Focus an editable field in another application. Tap **Ctrl+Shift+Space**, speak, and tap again to finish. The floating indicator does not take focus.
4. Recognized text is pasted into the focused target and remains on the clipboard. The previous clipboard is replaced. No Enter key is sent.

If the target window changes, modifier keys remain held, Windows blocks injection, or recognition flags uncertainty, text stays available in Voice Studio for review. Kotoba does not redirect a failed paste to an unrelated window. Standard native terminals receive Ctrl+Shift+V; ordinary apps receive Ctrl+V. Custom terminal bindings, elevated applications, browser-based terminals, password fields, and applications that reject synthetic input may require manual paste. A conflicting global hotkey is reported; it is not silently replaced.

Global dictation is an opt-in Windows feature. Leave Kotoba in the tray to use it while working in other apps. Meeting capture and dictation share one inference worker; finish one before starting the other. Dictation is capped at 60 seconds. **Add to chat** and **Ask voice agent** retain their explicit review/send boundary.

## Record a meeting

Open **Meetings & notes**, name the meeting, and select an audio source. Window titles select the owning application's process tree, which can include other windows and browser tabs. Closing the selected window stops capture explicitly. **All system audio** is a separate choice and is never a fallback for failed application capture.

Enable **Include my microphone** and select your microphone to capture your side as well. Use headphones to prevent speaker playback from being transcribed twice. Source labels distinguish capture channels; this release does not perform speaker diarization or acoustic echo cancellation.

The recorder prefers quiet chunk boundaries after ten seconds and caps chunks at thirty seconds. Each completed transcript is committed to local SQLite with timestamps, model identity, source, and review flags. **Stop & save** stops the inputs, waits for callbacks to finish, drains queued audio, and saves the partial final chunk. It does not depend on a mounted notes editor to save the final transcript.

The queue holds at most eight audio chunks, with a four-hour capture limit. If inference cannot keep up, capture stops with an explicit incomplete status while queued audio is saved. For two-channel Japanese meetings, compare real-time factor and select a faster model or compatible GPU if needed. Audio lives in memory and is not retained on disk; a crash can lose the active and queued audio. Completed transcript segments remain recoverable. Another running Kotoba process's meeting is not marked interrupted.

## Turn meetings into development references

Select a transcript line and choose **Highlight**, or use **Find key points** for extractive keyword suggestions covering English and Japanese decisions, owners, deadlines, and follow-ups. Suggestions preserve original wording and timestamps; they are not an AI-generated summary or verified commitments.

Development notes save automatically. Search titles, notes, and transcripts with English or Japanese text. Export Markdown with notes, highlights, source labels, and the full timestamped transcript. Delete a meeting to remove its note and transcript from the local database; exported copies and backups remain independent.

**Add to agent draft** prepares the meeting record for an AI recap and proposed development follow-ups. Review that draft in Voice Studio, choose the desired model, then send. Meeting text alone never automatically triggers agent tools. Agent permissions remain governed by the Harness.

## Local or cloud

**Processing: local** is the default on every launch. Local speech processing has no cloud fallback, analytics collection, or automatic audio upload. Captured audio stays in memory; notes and transcripts are unencrypted local data in `meetings.sqlite3`. Exporting is an explicit action. Model downloads contact GitHub or Hugging Face. Agent tools can access the network when the user invokes them.

Choose **Processing → Cloud** to configure an HTTPS OpenAI-compatible file-transcription endpoint, model, and session-only API key. The default endpoint uses OpenAI's file transcription API. Applying cloud mode authorizes audio and terminology hints to be uploaded for subsequent dictation, imports, and meetings. Provider fees and retention rules apply. Cloud failures do not retry automatically, follow redirects, or fall back to another provider. Generic providers return chunk timestamps rather than word timing; live provider credentials are required to qualify each service.

## 日本語

**音声スタジオ → 音声設定 → モデルを準備** でモデルをダウンロードしてください。英語は Parakeet Unified、日本語は Kotoba-Whisper v2、言語の自動判定は Whisper Turbo が推奨の初期設定です。Whisper large-v3 なども選択できます。文字起こしの精度は音声や専門用語に依存します。

**デスクトップ音声入力** を有効にし、入力したいアプリで **Ctrl+Shift+Space** を押すと録音を開始します。もう一度押すと文字起こしを貼り付けます。クリップボードも置き換えます。入力先の変更や確認が必要な結果は、音声スタジオで確認してください。

**会議とメモ** でウィンドウを選択すると、そのアプリのプロセス全体を録音します。同じブラウザーの他のタブが含まれる場合があります。自分のマイクも選択できます。ヘッドホンを使用してください。ラベルは録音元を示し、話者分離ではありません。

完了した文字起こしは時刻付きで端末に保存します。**停止して保存** で残りの音声も処理します。重要事項の候補はキーワード抽出なので、決定事項やタスクとして使う前に確認してください。開発メモは自動保存し、検索・Markdown 書き出し・エージェントの下書きへの追加ができます。

ローカル処理が既定で、クラウドへの自動切替はありません。クラウドを明示的に選択すると、音声と用語を指定した提供者へ送信します。API キーは今回の起動中のみ保持します。録音音声は保存しませんが、完了した文字起こしとメモは暗号化せず端末に保存します。クラッシュ時の未処理音声は復元できません。Windows の全体ホットキーとアプリ音声捕獲を実装しています。macOS/Linux 向けインストーラーや全体ホットキーは、この版の提供範囲に含まれません。

## Agent access

Use **Access** in the desktop toolbar to choose **Read-only**, **Workspace access**, or **Full access**. Select a particular existing chat or the default for new chats and the next voice conversation. Full access requires acknowledgment; the choice is stored in Harness, not only desktop preferences. Changing the default resets the idle voice SDK client so its next conversation picks up the new permission. Existing chats retain their setting until explicitly selected. A session change governs subsequent tool calls; it does not stop already-running commands.

These controls govern agent file and command tools. Chat displays interactive one-time approval requests; the voice SDK rejects requests without an available approval responder. Use **Add to chat** for interactive approvals. On Windows, the built-in sandbox primarily restricts writes and does not fully isolate reads or network traffic. Commands you type manually and privileged plugins are outside this agent policy. Full access still cannot exceed your operating-system account permissions.

デスクトップ上部の **アクセス** から、**読み取り専用**・**ワークスペース内の変更**・**フルアクセス** を選択します。既存のチャットを指定するか、新しいチャットと次の音声会話の既定値を設定できます。フルアクセスには確認が必要です。個別の承認はチャットに表示されます。音声 SDK は承認できない要求を拒否するため、対話的な承認には **チャットに追加** を使用してください。Windows では主に書き込みを制限し、読み取りやネットワークを完全には隔離しません。手入力のコマンドと権限を持つプラグインは対象外です。
