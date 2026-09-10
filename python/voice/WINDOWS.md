# Kotoba Studio for Windows

The installer is `python/voice/dist/Kotoba-Studio-0.5.0-Setup.exe` after a successful build. It installs for the current user, adds a Start menu entry, and supports English and Japanese installer text. The distribution includes Python, Qt WebEngine, the complete matching Harness executable, ripgrep, the OpenWhispr-derived capture helper, and the pinned llama.cpp CPU engine. Speech weights download on first use and are not included in the installer.

## Try the application

1. Install and launch **Kotoba Studio** on Windows 11 x64.
2. Complete workspace onboarding. Configure a key now or select **Configure later**.
3. In **Workspace**, choose a working folder. **Routing → Open full Kotoba Studio settings** opens the original Models panel, including **Add provider** and **Add a custom provider**. Supply the provider's endpoint, key, and model as applicable.
4. In **Voice**, select 日本語 or English, then expand **Audio settings** to choose Large-v3 or Turbo. **モデルを準備 / Download / warm model** downloads and loads the local speech model.
5. Select a microphone, system audio, or an application by window title. Press Record, then Transcribe. Capture ends after 60 seconds. Application capture includes the selected process's children; browser tabs may share processes. An unavailable source fails explicitly.
6. Review names, numbers, and intent. Use **Add to chat** to append reviewed text to the available chat draft, or use the voice panel's SDK session with DeepSeek or Kotoba Local. Cloud keys entered in the voice settings are session-only.
7. Explore **Code**, **Terminal**, and **Plugins**. The command console supports PowerShell commands; interactive terminal workflows remain in Harness. Installing external plugins can require separately installed developer tools such as pnpm.

Audio capture remains in memory. Only text you send goes to the model provider. Harness stores submitted conversations in its application data directory. Session exports are explicit. Uninstall preserves user data and downloaded models. The application is an unsigned developer preview; it has not completed code-signing, clean-machine compatibility, security, or production qualification. The upstream Harness version is itself an alpha.

Japanese/English voice input is supported. The top-right English/Japanese selector updates both the native panels and core embedded chat controls. Extension strings without Japanese translations fall back to English. Speaker diarization, streaming interruption, automatic provider failover, and system-wide paste-at-cursor dictation are not implemented in this milestone.

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
