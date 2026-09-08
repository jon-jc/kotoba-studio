from types import SimpleNamespace
from fastapi.testclient import TestClient
from kotoba.bridge import create_app

TOKEN = "test-only-" + "x" * 32


def test_bridge_authentication_and_full_sdk_response(tmp_path):
    sessions = []
    class Session:
        def __init__(self, home):
            self.closed = False
            sessions.append(self)
        def run(self, prompt, workspace, model, key, notify):
            assert "日本語で確認" in prompt
            return SimpleNamespace(final_response="確認しました。")
        def close(self):
            self.closed = True
    with TestClient(create_app(tmp_path / "home", TOKEN, tmp_path / "workspace", session_factory=Session)) as client:
        assert client.get("/health").status_code == 401
        headers = {"Authorization": "Bearer " + TOKEN}
        assert client.get("/health", headers=headers).status_code == 200
        response = client.post("/v1/chat/completions", headers=headers, json={"messages": [{"role": "user", "content": "日本語で確認"}], "stream": True})
        assert response.status_code == 200
        assert "確認しました。" in response.text
        assert "data: [DONE]" in response.text
        assert all(s.closed for s in sessions)


def test_unsupported_roles_fail_before_agent_execution(tmp_path):
    with TestClient(create_app(tmp_path, TOKEN, tmp_path)) as client:
        response = client.post("/v1/chat/completions", headers={"Authorization": "Bearer " + TOKEN}, json={"messages": [{"role": "tool", "content": "execute"}]})
        assert response.status_code == 400
