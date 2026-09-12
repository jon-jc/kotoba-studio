# Kotoba Studio for Windows

The installer is `python/voice/dist/Kotoba-Studio-0.7.1-Setup.exe` after a successful build. It installs for the current user, adds a Start menu entry, and supports English and Japanese installer text. The distribution includes Python, Qt WebEngine, the complete matching Harness executable, ripgrep, the OpenWhispr-derived capture helper, and the pinned llama.cpp CPU engine. Prepare speech weights explicitly in Audio settings; weights are not included in the installer. The installer bundles sherpa-onnx and faster-whisper.

## Try the application

1. Install and launch **Kotoba Studio** on Windows 11 x64.
2. Complete workspace onboarding. Configure a key now or select **Configure later**.
3. In **Workspace**, choose a working folder. **Routing → Open full Kotoba Studio settings** opens the original Models panel, including **Add provider** and **Add a custom provider**. Supply the provider's endpoint, key, and model as applicable.
4. In **Voice**, select 日本語 or English, then expand **Audio settings** to choose Parakeet for English, Kotoba Whisper for Japanese, or another supported model. **モデルを準備 / Download / warm model** downloads and loads the local speech model.
5. Select a microphone, system audio, or an application by window title. Press Record, then Transcribe. Short dictation ends after 60 seconds; use Meetings & notes for longer sessions. Application capture includes the selected process's children; browser tabs may share processes. An unavailable source fails explicitly.
6. Review names, numbers, and intent. Use **Add to chat** to append reviewed text to the available chat draft, or use the voice panel's SDK session with a configured provider and model. Cloud keys entered in the voice settings are session-only.
7. Explore **Code**, **Terminal**, and **Plugins**. The command console supports PowerShell commands; interactive terminal workflows remain in Harness. Installing external plugins can require separately installed developer tools such as pnpm.

Audio capture remains in memory. Only text you send goes to the model provider. Harness stores submitted conversations in its application data directory. Session exports are explicit. Uninstall preserves user data and downloaded models. The application is an unsigned developer preview; it has not completed code-signing, clean-machine compatibility, security, or production qualification. The upstream Harness version is itself an alpha.

Japanese/English voice input is supported. The top-right English/Japanese selector updates both the native panels and core embedded chat controls. Extension strings without Japanese translations fall back to English. Windows global paste-at-cursor dictation and durable meeting notes are described in the [voice guide](VOICE.md). Speaker diarization, streaming interruption, and automatic provider failover are not implemented.

The chat welcome headline is **Create with Kotoba** in English and **ことばを、かたちに。** in Japanese.

Click the top-left **Kotoba Studio** icon or name to return to chat and open its workspace sidebar from any panel. Open code tabs, terminal output, and voice drafts remain available when you return to those panels.

## Code workspace

Click **Code** again or **Close Code** to return to chat; open file tabs are retained. **Esc** closes search first, then the Code page. **Ctrl+W** closes the active file, or returns to chat when no file is open. Explorer shows the selected folder, file tabs support comparison, and the path bar uses workspace-relative paths. **Find in file / Ctrl+F** opens search only when a file is available. The viewer remains read-only.

## Workspace selection

**Add workspace** opens a folder browser inside the app from both the expanded sidebar and the collapsed icon rail. Enter a path with the pencil control or browse folders, then select **Open**. The desktop composes the browse backend and its matching interface through a packaged profile overlay; the automatic native picker is disabled for this launch. This avoids an unowned OS chooser appearing behind the desktop window. English and Japanese labels follow the language selector.

The voice panel tabs and closed dropdowns keep their selection while scrolling. Click a tab or open a dropdown to choose an option; keyboard navigation remains available.

## Motion and recovery

The **···** menu includes **Reduce motion / 動きを減らす**, saved across launches. Voice and terminal panels fade in briefly; chat buttons and popups use short transitions. The Windows animation preference also suppresses native reveals, and embedded chat respects the system reduced-motion preference. Panels remain immediately usable during transitions. Access settings includes **Reload** after connection or revision errors. Recording keeps its Stop control available while the voice dock is reopened.

## System tray

Closing the main window keeps the app in the system tray when available. Use the tray menu to restore the workspace, open Voice Studio, or quit. Quit stops the owned runtime and local engine; active recording or processing must finish first. The installer assigns the same Kotoba Studio icon and Windows application identity to the Start menu and optional desktop shortcuts. Re-pin an older Python shortcut from the updated Start menu entry if Windows retains its previous icon.

## Build

The PowerShell console initializes UTF-8 before reading its first command and decodes output across chunk boundaries, preserving Japanese text. The Windows test executes Japanese commands and checks their output and persistent session state.

Use the repository's matching runtime build described in [the Python runtime README](../sdk-runtime/README.md). Build the capture helper from [its source](native/windows-system-audio-helper.c) using a Windows C compiler; place `kotoba-audio-capture.exe` beside the matching runtime and ripgrep executables under `dist-exe/`. The source includes MSVC and MinGW commands. Install `python/voice[build]` and the same-checkout Python SDK in your environment.

```powershell
python python/voice/prepare_local_runtime.py
python python/voice/build_windows.py --iscc "C:/path/to/Inno Setup/ISCC.exe"
python python/voice/verify_windows.py python/voice/dist/Kotoba/Kotoba.exe --output tmp/frozen-verification
```

The build controls DLL search paths to avoid collecting incompatible ICU libraries from unrelated developer tools. The verifier launches the actual executable, probes the native audio helper, imports native speech dependencies, tests silence handling, and verifies the original Harness browser composition loads. It does not claim a paid provider request succeeded.

## 日本語

インストーラーで現在のユーザー向けにインストールし、スタートメニューから起動します。音声モデルは初回にダウンロードされます。録音元と言語を選び、録音・文字起こしの後に名前と数字を確認してから送信してください。アプリ指定録音はプロセスツリー単位で、ブラウザーのタブ単位とは限りません。署名と本番運用の検証は未完了です。

## Native local models

Open **Local models** and select a compatible GGUF instruction model. **Start / discover** loads it on CPU; **Use selected model for voice and register in chat** selects it for voice. Choose **Kotoba Local** separately in the full chat composer. Ollama and LM Studio are optional alternative connections on the same page. See [local model behavior and limits](README.md#local-language-models). The installer bundles the inference engine and license notices, not language-model weights. Preparation verifies the release archive against [the pinned SHA-256](native/llama-runtime.json).

**ローカルモデル** 画面で GGUF を選択すると、同梱の CPU エンジンで実行できます。モデルの重みは別途用意してください。登録後、チャットのモデル選択で **Kotoba Local** を選びます。アプリの再起動後はエンジンを再度起動してください。

Kotoba Studio starts without the upstream Internal Testing Notice. Provider setup remains available; choose Configure later to use the Local models page.
