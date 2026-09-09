"""Verify an installed/frozen application boots the real Harness composition."""

import argparse
import json
import os
import http.cookiejar
from pathlib import Path
import queue
import re
import subprocess
import tempfile
import threading
import urllib.request


def verify_inventory(exe):
    """Exercise a read-only remote against the bundled production composition."""
    runtime = exe.resolve().parent / "runtime" / "deepseek-harness-sdk-runtime-win-x64.exe"
    with tempfile.TemporaryDirectory(prefix="kotoba-inventory-") as home:
        env = {**os.environ, "DSH_HOME": home, "DSH_TELEMETRY_DISABLED": "1"}
        process = subprocess.Popen([str(runtime), "web", "--no-open", "--host", "127.0.0.1", "--port", "0"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        urls = queue.Queue()
        def read():
            for line in process.stdout:
                match = re.search(r"http://127\.0\.0\.1:\d+/\?token=[A-Za-z0-9_-]+", line)
                if match:
                    urls.put(match.group())
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        try:
            url = urls.get(timeout=65)
            origin = url.split("/?", 1)[0]
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            opener.open(url, timeout=15).close()
            request = urllib.request.Request(origin + "/api/pluginInventory/list", method="POST",
                headers={"Content-Type": "application/json", "Origin": origin},
                data=json.dumps({"type": "client-request", "rpcId": "kotoba-verification", "method": "pluginInventory/list", "payload": {"args": {}}}).encode())
            with opener.open(request, timeout=30) as response:
                result = json.load(response)["result"]
            if not result.get("ok") or not result["value"].get("entries"):
                raise RuntimeError("Bundled Harness plugin inventory failed: " + json.dumps(result))
            return {"host_plugins": len(result["value"]["entries"]), "agent_presets": len(result["value"].get("agentPresets", []))}
        finally:
            if process.poll() is None:
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
            process.wait(timeout=10)
            reader.join(timeout=2)
            process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["KOTOBA_SCREENSHOT"] = str((args.output / "workspace.png").resolve())
    env["KOTOBA_VERIFY_REPORT"] = str((args.output / "dependencies.json").resolve())
    for name in ("workspace.json", "dependencies.json"):
        (args.output / name).unlink(missing_ok=True)
    for mode in ("--diagnostics", "--smoke"):
        subprocess.run([str(args.exe.resolve()), mode], env=env, check=True, timeout=100)
    checks = [json.loads((args.output / name).read_text(encoding="utf-8")) for name in ("workspace.json", "dependencies.json")]
    if not checks[0].get("runtime_ready") or not checks[1].get("ok"):
        raise RuntimeError("The frozen application did not pass its composition checks.")
    inventory = verify_inventory(args.exe)
    (args.output / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print("Installed application: dependency check and real Harness UI boot passed.")


if __name__ == "__main__":
    main()
