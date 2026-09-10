"""Desktop access choices use Harness settings and its audited permission command."""

import re
from .local_models import HarnessRemote

MODES = ("read-only", "workspace-write", "danger-full-access")


class AccessSettings:
    def __init__(self, url):
        self.url = url
        self._remote = None

    @property
    def remote(self):
        if self._remote is None:
            self._remote = HarnessRemote(self.url)
        return self._remote

    def describe(self):
        view = self.remote.call("settings/describe", {})
        section = next(item for item in view["namespaces"] if item["ns"] == "permission")
        sessions = self.remote.call("session/list", {})["items"]
        return {"mode": section["value"]["defaultPreset"], "revision": section["revision"],
                "sessions": [s for s in sessions if not s["sessionId"].startswith("kotoba-") and not s.get("parentSessionId")]}

    def set_default(self, mode, revision):
        if mode not in MODES:
            raise ValueError("Unknown access level")
        self.remote.call("settings/mutate", {"ns": "permission", "expectedRevision": revision,
            "ops": [{"op": "set", "path": ["defaultPreset"], "value": mode}]})
        return self.describe()

    def session_mode(self, session_id, mode=None):
        if mode is not None and mode not in MODES:
            raise ValueError("Unknown access level")
        self.remote.call("session/create", {"request": {"sessionId": session_id}})
        result = self.remote.call("commands/execute", {"agentId": session_id,
            "line": "/permission" + (" " + mode if mode else ""), "submittedAttachments": []})
        if not result or result["result"]["kind"] != "success":
            raise RuntimeError("Access change failed. / アクセス設定を変更できませんでした。")
        if mode:
            return mode
        match = re.fullmatch(r"current preset ([^ ]+) \(available: .+\)", result["result"].get("text", ""))
        if match is None:
            raise RuntimeError("Cannot read this session's access level. / 会話のアクセス設定を取得できません。")
        return match[1]
