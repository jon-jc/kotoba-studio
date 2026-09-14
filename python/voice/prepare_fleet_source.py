"""Apply the reviewed Kotoba overlay to a disposable, pinned Orca build checkout."""

import argparse
from pathlib import Path
import subprocess
import shutil

ORCA_REVISION = "8641b3af0970b030cebbc263233585cc1ef83a4b"


def replace_once(root, relative, before, after):
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if after in text:
        return
    if text.count(before) != 1:
        raise ValueError(f"Orca overlay no longer matches {relative}")
    path.write_text(text.replace(before, after), encoding="utf-8", newline="\n")


def prepare(root):
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != ORCA_REVISION:
        raise ValueError("Build requires the reviewed Orca revision " + ORCA_REVISION)
    replace_once(root, "src/main/startup/configure-process.ts",
        "export function configureDevUserDataPath(isDev: boolean): void {",
        "export function configureDevUserDataPath(isDev: boolean): void {\n"
        "  if (process.env.KOTOBA_FLEET_HOME) {\n"
        "    const profile = resolve(process.env.KOTOBA_FLEET_HOME)\n"
        "    mkdirSync(profile, { recursive: true, mode: 0o700 })\n"
        "    app.setPath('userData', profile)\n"
        "    return\n  }")
    replace_once(root, "src/main/startup/main-process-runtime-launch.ts",
        "    exposeNetworkByDefault: Boolean(serveOptions) || isE2E,",
        "    exposeNetworkByDefault: Boolean(serveOptions) || isE2E,\n"
        "    ...(process.env.KOTOBA_FLEET_HOME ? { pinnedBindHost: '127.0.0.1' } : {}),")
    replace_once(root, "vite.web.config.ts", "ORCA_FEATURE_WALL_ENABLED: 'true'", "ORCA_FEATURE_WALL_ENABLED: 'false'")
    replace_once(root, "src/renderer/web-index.html", "<title>Orca Web</title>", "<title>Kotoba Studio · Agent Fleet</title>")
    replace_once(root, "src/renderer/src/web/main.tsx", "import '../assets/main.css'",
        "import '../assets/main.css'\nimport './kotoba-fleet'")
    replace_once(root, "src/renderer/src/main.tsx", "import './assets/main.css'",
        "import './assets/main.css'\nimport './web/kotoba-fleet'")
    replace_once(root, "src/main/window/createMainWindow.ts",
        "import { BrowserWindow, nativeTheme, powerMonitor, screen } from 'electron'",
        "import { BrowserWindow, nativeTheme, powerMonitor, screen } from 'electron'\nimport { installKotobaWindowHost } from './kotoba-window-host'")
    replace_once(root, "src/main/window/createMainWindow.ts", "    show: false,",
        "    show: false,\n    ...(process.env.KOTOBA_FLEET_HOME ? { frame: false } : {}),")
    replace_once(root, "src/main/window/createMainWindow.ts", "  return mainWindow",
        "  installKotobaWindowHost(mainWindow)\n  return mainWindow")
    replace_once(root, "src/main/tray/system-tray.ts", "export function createSystemTray(opts: SystemTrayOptions): Tray | null {",
        "export function createSystemTray(opts: SystemTrayOptions): Tray | null {\n  if (process.env.KOTOBA_FLEET_HOME) return null")
    replace_once(root, "src/renderer/src/app-shell/app-window-chrome.ts",
        "export const hasCustomTitleBar = shouldRenderDesktopWindowChrome({",
        "export const hasCustomTitleBar = false && shouldRenderDesktopWindowChrome({")
    replace_once(root, "src/renderer/src/app-shell/AppRootSurfaces.tsx",
        "{onboardingGate.onboarding && onboardingGate.shouldRender ? (",
        "{activeView !== 'settings' && onboardingGate.onboarding && onboardingGate.shouldRender ? (")
    replace_once(root, "src/shared/default-global-settings.ts", "    theme: 'system',", "    theme: 'dark',")
    replace_once(root, "src/shared/default-global-settings.ts", "    rightSidebarOpenByDefault: true,", "    rightSidebarOpenByDefault: false,")
    replace_once(root, "src/shared/constants.ts", "    rightSidebarOpen: true,", "    rightSidebarOpen: false,")
    replace_once(root, "src/renderer/src/components/Landing.tsx",
        "import logo from '../../../../resources/logo.svg'",
        "import logo from '../../../../resources/icon.png'")
    for signature in (
        "export function checkForUpdates(): void {",
        "export function checkForUpdatesFromMenu(options?: UpdateCheckOptions): void {",
        "export function downloadUpdate(): void {",
        "export function quitAndInstall(): void {",
        "export function setupAutoUpdater(mainWindow: BrowserWindow, opts?: UpdaterSetupOptions): void {",
    ):
        replace_once(root, "src/main/updater.ts", signature,
            signature + "\n  if (process.env.KOTOBA_FLEET_HOME) return")
    replace_once(root, "src/shared/tui-agent-launch-defaults.ts",
        "export const DEFAULT_TUI_AGENT_ARGS: Partial<Record<TuiAgent, string>> = YOLO_TUI_AGENT_ARGS",
        "export const DEFAULT_TUI_AGENT_ARGS: Partial<Record<TuiAgent, string>> = {}")
    replace_once(root, "src/shared/tui-agent-launch-defaults.ts", "  YOLO_TUI_AGENT_ENV", "  {}")
    replace_once(root, "src/shared/tui-agent-launch-defaults.ts", "import { YOLO_TUI_AGENT_ARGS, YOLO_TUI_AGENT_ENV } from './tui-agent-permissions'\n", "// Agent CLIs retain their own approval defaults in Kotoba.\n")
    integration = root / "src/renderer/src/web/kotoba-fleet.ts"
    shutil.copyfile(Path(__file__).with_name("fleet_workspace_bridge.ts"), integration)
    shutil.copyfile(Path(__file__).with_name("fleet_window_host.ts"), root / "src/main/window/kotoba-window-host.ts")
    mark = Path(__file__).resolve().parents[2] / "assets/brand/kotoba-mark.png"
    for icon in ("icon.png", "icon-dev.png", "app-icons/orca-watercolor.png", "app-icons/orca-blue.png"):
        shutil.copyfile(mark, root / "resources" / icon)
    shutil.copyfile(Path(__file__).with_name("assets") / "kotoba.svg", root / "resources/logo.svg")
    shutil.copyfile(Path(__file__).with_name("fleet_workspace.css"), root / "src/renderer/src/assets/kotoba-workspace.css")
    replace_once(root, "src/renderer/src/main.tsx", "import './web/kotoba-fleet'", "import './web/kotoba-fleet'\nimport './assets/kotoba-workspace.css'")
    from prepare_fleet_access import prepare_access
    prepare_access(root, replace_once)
    from prepare_fleet_sidebar import prepare_sidebar
    prepare_sidebar(root)
    from prepare_fleet_chat import prepare_chat, prepare_chat_experience, prepare_claude_chat_compatibility
    prepare_chat(root, replace_once)
    prepare_chat_experience(root, replace_once)
    prepare_claude_chat_compatibility(root, replace_once)
    from prepare_fleet_locale import prepare_locale
    prepare_locale(root)
    replace_once(root, 'src/preload/index.ts',
        "import { contextBridge, ipcRenderer } from 'electron'",
        "import { contextBridge, ipcRenderer } from 'electron'\n"
        "// Chromium needs native focus after Qt adopts its window. Do not expose this\n"
        "// channel to page scripts or forward synthetic gestures from embedded pages.\n"
        "if (process.isMainFrame) {\n"
        "  window.addEventListener('pointerdown', event => {\n"
        "    if (event.isTrusted) ipcRenderer.send('kotoba:focusEmbedded')\n"
        "  }, { capture: true, passive: true })\n"
        "}")
    shutil.copyfile(Path(__file__).with_name('fleet_windows_codex.ts'), root / 'src/shared/kotoba-windows-codex.ts')
    shutil.copyfile(Path(__file__).with_name('fleet_windows_codex.test.ts'), root / 'src/shared/kotoba-windows-codex.test.ts')
    replace_once(root, 'src/shared/system-cli-install-dirs.ts',
        "import { join } from 'node:path'",
        "import { join } from 'node:path'\nimport { windowsCodexDirectories } from './kotoba-windows-codex'")
    replace_once(root, 'src/shared/system-cli-install-dirs.ts',
        "  if (platform === 'win32') {\n    return []",
        "  if (platform === 'win32') {\n    return windowsCodexDirectories(platform, homePath)")
    replace_once(root, 'src/shared/system-cli-install-dirs.ts',
        "  // Why nothing here: the PATH seed's system block is POSIX-only too, so\n  // Windows installs outside a version manager (`%USERPROFILE%\\.opencode\\bin`)\n  // have never had install-dir coverage in either list. Unchanged, not fixed.",
        "  // Desktop Codex uses versioned user-local directories absent from GUI PATH.")
    replace_once(root, 'src/main/startup/configure-process.ts',
        "import { app } from 'electron'",
        "import { app } from 'electron'\nimport { windowsCodexDirectories } from '../../shared/kotoba-windows-codex'")
    replace_once(root, 'src/main/startup/configure-process.ts',
        "  const currentSegments = currentPath.split(pathDelimiter).filter(Boolean)",
        "  appendPaths.push(...windowsCodexDirectories())\n  const currentSegments = currentPath.split(pathDelimiter).filter(Boolean)")
    replace_once(root, 'src/main/ipc/agent-detection-shell-path.ts',
        "import { hydrateShellPath, mergePathSegments }",
        "import { windowsCodexDirectories } from '../../shared/kotoba-windows-codex'\nimport { hydrateShellPath, mergePathSegments }")
    replace_once(root, 'src/main/ipc/agent-detection-shell-path.ts',
        "    mergePathSegments(hydration.segments)\n  }",
        "    mergePathSegments(hydration.segments)\n  }\n  const codexDirectories = windowsCodexDirectories()\n  if (codexDirectories.length) {\n    // Preserve explicit shell choices; refresh installs added after app startup.\n    const existing = (process.env.PATH ?? process.env.Path ?? '').split(';').filter(Boolean)\n    mergePathSegments([...existing, ...codexDirectories])\n  }")
    replace_once(root, 'src/main/preflight/agent-detection.ts',
        "import { hydrateShellPath, mergePathSegments }",
        "import { windowsCodexDirectories } from '../../shared/kotoba-windows-codex'\nimport { hydrateShellPath, mergePathSegments }")
    replace_once(root, 'src/main/preflight/agent-detection.ts',
        '  const added = hydration.ok ? mergePathSegments(hydration.segments) : []',
        "  const added = hydration.ok ? mergePathSegments(hydration.segments) : []\n  const codexDirectories = windowsCodexDirectories()\n  if (codexDirectories.length) {\n    const existing = (process.env.PATH ?? process.env.Path ?? '').split(';').filter(Boolean)\n    added.push(...mergePathSegments([...existing, ...codexDirectories]))\n  }")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    prepare(parser.parse_args().checkout.resolve())
