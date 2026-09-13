"""Apply the reviewed Kotoba overlay to a disposable, pinned Orca build checkout."""

import argparse
from pathlib import Path
import subprocess

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
    integration = root / "src/renderer/src/web/kotoba-fleet.ts"
    integration.write_text('''// Kotoba desktop integration; runtime operations remain owned by Orca.
import { i18n } from '../i18n/i18n'
import { useAppStore } from '../store'

i18n.use({ type: 'postProcessor', name: 'kotobaBrand', process: (value: string) => value.replace(/\\bOrca\\b/g, 'Kotoba Fleet') })
i18n.options.postProcess = ['kotobaBrand']
Object.assign(window, { kotobaFleetReady: true })
window.addEventListener('kotoba-locale', (event) => {
  const language = (event as CustomEvent<unknown>).detail
  if (language !== 'en' && language !== 'ja') return
  void i18n.changeLanguage(language)
  const state = useAppStore.getState()
  if (state.settings && state.settings.uiLanguage !== language) {
    void state.updateSettings({ uiLanguage: language })
  }
})
''', encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    prepare(parser.parse_args().checkout.resolve())
