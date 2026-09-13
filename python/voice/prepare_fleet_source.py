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
    from prepare_fleet_access import prepare_access
    prepare_access(root, replace_once)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    prepare(parser.parse_args().checkout.resolve())
