# Kotoba Studio for Windows

The installer is `python/voice/dist/Kotoba-Studio-0.2.0-Setup.exe` after a successful build. It installs for the current user, adds a Start menu entry, and supports English and Japanese installer text. The distribution includes Python, Qt WebEngine, the complete matching Harness executable, ripgrep, and the OpenWhispr-derived capture helper. Speech weights download on first use and are not included in the installer.

## Try the application

1. Install and launch **Kotoba Studio** on Windows 11 x64.
2. Complete Harness onboarding. Configure a key now or select **Configure later**.
3. In **Workspace**, choose a working folder. **Routing → Open full Harness settings** opens the original Models panel, including **Add provider** and **Add a custom provider**. Supply the provider's endpoint, key, and model as applicable.
4. In **Voice**, select 日本語 or English, then Large-v3 or Turbo. **モデルを準備 / Download / warm model** downloads and loads the local speech model.
5. Select a microphone, system audio, or an application by window title. Press Record, then Transcribe. Capture ends after 60 seconds. Application capture includes the selected process's children; browser tabs may share processes. An unavailable source fails explicitly.
6. Review names, numbers, and intent. Copy the reviewed text into any Harness chat, or use the voice panel's separate DeepSeek SDK session. Its API key is session-only.
7. Explore **Code**, **Terminal**, and **Plugins**. The command console supports PowerShell commands; interactive terminal workflows remain in Harness. Installing external plugins can require separately installed developer tools such as pnpm.

Audio capture remains in memory. Only text you send goes to the model provider. Harness stores submitted conversations in its application data directory. Session exports are explicit. Uninstall preserves user data and downloaded models. The application is an unsigned developer preview; it has not completed code-signing, clean-machine compatibility, security, or production qualification. The upstream Harness version is itself an alpha.

Japanese/English voice input is supported. The original Harness interface retains its upstream English/Chinese locale set; the added voice interface supports Japanese/English. Speaker diarization, streaming interruption, automatic provider failover, and system-wide paste-at-cursor dictation are not implemented in this milestone.

## Build

Use the repository's matching runtime build described in [the Python runtime README](../sdk-runtime/README.md). Build the capture helper from [its source](native/windows-system-audio-helper.c) using a Windows C compiler; place `kotoba-audio-capture.exe` beside the matching runtime and ripgrep executables under `dist-exe/`. The source includes MSVC and MinGW commands. Install `python/voice[build]` and the same-checkout Python SDK in your environment.

```powershell
python python/voice/build_windows.py --iscc "C:/path/to/Inno Setup/ISCC.exe"
python python/voice/verify_windows.py python/voice/dist/Kotoba/Kotoba.exe --output tmp/frozen-verification
```

The build controls DLL search paths to avoid collecting incompatible ICU libraries from unrelated developer tools. The verifier launches the actual executable, probes the native audio helper, imports native speech dependencies, tests silence handling, and verifies the original Harness browser composition loads. It does not claim a paid provider request succeeded.

## 日本語

インストーラーで現在のユーザー向けにインストールし、スタートメニューから起動します。音声モデルは初回にダウンロードされます。録音元と言語を選び、録音・文字起こしの後に名前と数字を確認してから送信してください。アプリ指定録音はプロセスツリー単位で、ブラウザーのタブ単位とは限りません。署名と本番運用の検証は未完了です。
