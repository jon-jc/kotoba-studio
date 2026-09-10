"""Build a Windows desktop distribution from an already-built matching Harness runtime."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from build_icon import build_icon


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, help="Inno Setup compiler; omit to build only the application folder")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Build the Windows application on Windows.")
    voice = Path(__file__).resolve().parent
    build_icon()
    root = voice.parents[1]
    binaries = [root / "dist-exe" / name for name in (
        "deepseek-harness-sdk-runtime-win-x64.exe", "deepseek-harness-sdk-runtime-win-x64-rg.exe",
        "kotoba-audio-capture.exe")]
    for binary in binaries:
        if not binary.is_file():
            parser.error(f"Build the required runtime first: {binary}")
    local_engine = root / "dist-exe" / "llama"
    if not (local_engine / "llama-server.exe").is_file():
        parser.error("Run python python/voice/prepare_local_runtime.py first.")
    environment = os.environ.copy()
    # Resolve Windows system DLLs before unrelated developer-tool DLLs.
    # In particular, third-party ICU builds do not export Windows ICU symbols.
    windows = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(map(str, [windows / "System32", windows, Path(sys.executable).parent, Path(sys.base_prefix)]))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
        "--name", "Kotoba", "--distpath", str(voice / "dist"), "--workpath", str(voice / "build"),
        "--icon", str(voice / "assets" / "kotoba.ico"), "--add-data", str(voice / "assets") + ";assets",
        "--version-file", str(voice / "assets" / "windows-version.txt"),
        "--specpath", str(voice), "--paths", str(voice / "src"),
        "--collect-all", "faster_whisper", "--collect-all", "ctranslate2", "--collect-all", "av",
        "--collect-submodules", "deepseek_harness", "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto", "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto", "--hidden-import", "uvicorn.lifespan.on",
        str(voice / "launcher.py")], check=True, cwd=root, env=environment)
    output = voice / "dist" / "Kotoba"
    runtime = output / "runtime"
    runtime.mkdir(exist_ok=True)
    for binary in binaries:
        shutil.copy2(binary, runtime / binary.name)
    shutil.copytree(local_engine, runtime / "llama", dirs_exist_ok=True)
    licenses = output / "licenses"
    licenses.mkdir(exist_ok=True)
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, licenses / name)
    shutil.copytree(voice / "THIRD_PARTY_LICENSES", licenses, dirs_exist_ok=True)
    if args.iscc:
        subprocess.run([str(args.iscc.resolve()), str(voice / "installer.iss")], check=True)
    print(output)


if __name__ == "__main__":
    main()
