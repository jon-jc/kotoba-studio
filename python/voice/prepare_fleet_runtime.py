"""Build the pinned subscription-agent workspace for the Windows installer.

Use a short disposable checkout path on Windows so native C++ build paths fit.
The submodule is the source of record; no generated files modify it.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from prepare_fleet_source import prepare, ORCA_REVISION


def run(command, root, environment):
    subprocess.run(command, cwd=root, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True, help="Disposable pinned Orca checkout")
    parser.add_argument("--skip-install", action="store_true", help="Reuse already installed, rebuilt dependencies")
    parser.add_argument("--skip-build", action="store_true", help="Package an already built overlay")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("The embedded workspace currently targets Windows x64.")
    voice = Path(__file__).resolve().parent
    root = voice.parents[1]
    checkout = args.checkout.resolve()
    if checkout == (root / "integrations/orca").resolve():
        parser.error("Use a disposable checkout; keep the pinned submodule clean.")
    if not checkout.exists():
        run(["git", "clone", "--no-hardlinks", str(root / "integrations/orca"), str(checkout)], root, os.environ.copy())
        run(["git", "checkout", "--detach", ORCA_REVISION], checkout, os.environ.copy())
    prepare(checkout)
    environment = os.environ.copy()
    environment.update(ORCA_BACKGROUND_LAUNCH="1", DO_NOT_TRACK="1", ORCA_TELEMETRY_DISABLED="1",
        KOTOBA_ORCA_CHECKOUT=str(checkout), KOTOBA_FLEET_OUTPUT=str(root / "dist-exe/fleet-package"))
    environment.pop("ORCA_ELECTRON_VITE_TARGET", None)
    if not args.skip_install:
        run(["pnpm.cmd", "install", "--frozen-lockfile"], checkout, environment)
    run(["node", "config/scripts/ensure-native-runtime.mjs", "--runtime=electron", "--check-only"], checkout, environment)
    if not args.skip_build:
        run(["node", "config/scripts/build-relay.mjs"], checkout, environment)
        run(["node", "config/scripts/build-native-for-platform.mjs"], checkout, environment)
        run([str(checkout / "node_modules/.bin/tsc.cmd"), "-p", "config/tsconfig.cli.json", "--outDir", "out", "--composite", "false", "--incremental", "false"], checkout, environment)
        run(["node", "config/scripts/run-electron-vite-build.mjs"], checkout, environment)
        run(["node", "config/scripts/run-vite-web-build.mjs"], checkout, environment)
    run(["node", "config/scripts/verify-cli-bin.mjs", "--fix-executable", "--fix-package-json"], checkout, environment)
    run(["node", "node_modules/electron-builder/out/cli/cli.js", "--config", str(voice / "fleet_builder.cjs"), "--win", "--x64", "--dir"], checkout, environment)
    output = root / "dist-exe/fleet-package/win-unpacked"
    if not (output / "KotobaAgents.exe").is_file() or not (output / "resources/app.asar").is_file():
        raise RuntimeError("Packaged agent runtime is incomplete")
    (output / "manifest.json").write_text(json.dumps({"schema": 1, "revision": ORCA_REVISION,
        "executable": "KotobaAgents.exe", "entry": "resources/app.asar"}, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(checkout / "LICENSE", output / "LICENSE-Orca.txt")
    # Publish only after the upstream package checks have completed successfully.
    target = root / "dist-exe/fleet"
    if target.exists():
        if target.resolve().parent != (root / "dist-exe").resolve() or target.is_symlink():
            raise RuntimeError("Unexpected runtime output location")
        shutil.rmtree(target)
    shutil.copytree(output, target)
    print(target)


if __name__ == "__main__":
    main()
