import base64
import hashlib
import hmac
import json
import sqlite3
import sys
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient
from kotoba.messaging_store import MessagingStore, protect, validate_config, PLATFORMS
from kotoba.messaging_adapters import PlatformAdapter, MessagingError, line_events, message
from kotoba.messaging_gateway import line_app, LineReceiver, GatewayWorker, MessagingGateway

USER = "U" + "a" * 32


def test_line_registration_tests_receiver_before_changing_endpoint():
    calls = []
    endpoint = "https://kotoba.example/line/fixture"
    def transport(request):
        calls.append((request.method, request.url.path))
        if request.method in ("POST", "PUT"):
            assert json.loads(request.content) == {"endpoint": endpoint}
        return httpx.Response(200, json={"success": True} if request.method == "POST" else {"active": False})
    adapter = PlatformAdapter(config(), {"token": "fixture"}, httpx.MockTransport(transport))
    try:
        assert adapter.configure_line_webhook(endpoint, True)["active"] is False
        assert calls == [("POST", "/v2/bot/channel/webhook/test"), ("PUT", "/v2/bot/channel/webhook/endpoint"), ("GET", "/v2/bot/channel/webhook/endpoint")]
        calls.clear()
        assert adapter.configure_line_webhook(endpoint) == {}
        assert calls == [("POST", "/v2/bot/channel/webhook/test")]
    finally:
        adapter.close()


@pytest.mark.parametrize("response", [{"success": False}, {}, []])
def test_line_failed_verification_never_changes_endpoint(response):
    calls = []
    def transport(request):
        calls.append(request.method)
        return httpx.Response(200, json=response)
    adapter = PlatformAdapter(config(), {"token": "fixture"}, httpx.MockTransport(transport))
    try:
        with pytest.raises(MessagingError):
            adapter.configure_line_webhook("https://kotoba.example/line/fixture", True)
        assert calls == ["POST"]
        for endpoint in ["http://kotoba.example/line/x", "https://user:password@kotoba.example/x", "https://kotoba.example/x?secret=a", "https://kotoba.example/" + "x" * 500]:
            with pytest.raises(MessagingError):
                adapter.configure_line_webhook(endpoint, True)
        assert calls == ["POST"]
    finally:
        adapter.close()


def config(platform="line"):
    user = {"line": USER, "slack": "U123", "discord": "123", "telegram": "123"}[platform]
    return dict(platform=platform, name=platform, users=[user], targets=[], channel="C123" if platform == "slack" else "456" if platform == "discord" else "",
                provider="openai", model="fixture-model", language="ja", enabled=True)


@pytest.fixture
def saved(tmp_path):
    if sys.platform != "win32":
        pytest.skip("Windows user-bound credential store")
    store = MessagingStore(tmp_path)
    identity = store.save_config(None, config(), "fixture-private-token", "fixture-private-secret")
    return store, identity


def line_payload(user=USER, group=None):
    source = {"type": "group", "groupId": group, "userId": user} if group else {"type": "user", "userId": user}
    return json.dumps({"events": [{"type": "message", "source": source, "message": {"type": "text", "id": "m1", "text": "明日の確認をお願いします。 <script>"}}]}, ensure_ascii=False).encode()


def signature(raw):
    return base64.b64encode(hmac.new(b"fixture-private-secret", raw, hashlib.sha256).digest()).decode()


def test_windows_credentials_are_not_plaintext_and_survive_reopen(saved):
    store, identity = saved
    assert b"fixture-private-token" not in store.path.read_bytes()
    assert b"fixture-private-secret" not in store.path.read_bytes()
    assert MessagingStore(store.path.parent).credentials(identity)["token"] == "fixture-private-token"
    store.save_config(identity, config(), "", "")
    assert store.credentials(identity)["secret"] == "fixture-private-secret"
    assert "token" not in json.dumps(store.configs())
    store.delete(identity)
    assert store.configs() == []


def test_sender_allowlist_is_required_and_line_is_first():
    assert PLATFORMS[0] == "line"
    for platform in PLATFORMS:
        value = config(platform)
        validate_config(value)
        value["users"] = []
        with pytest.raises(ValueError):
            validate_config(value)


def test_line_signature_verified_before_parsing_and_groups_are_explicit():
    raw = line_payload()
    rows = line_events(raw, signature(raw), config(), "fixture-private-secret")
    assert rows[0]["text"] == "明日の確認をお願いします。 <script>"
    for bad in ("", signature(raw + b" ")):
        with pytest.raises(PermissionError):
            line_events(raw, bad, config(), "fixture-private-secret")
    denied = line_payload("U" + "b" * 32)
    assert line_events(denied, signature(denied), config(), "fixture-private-secret") == []
    grouped = line_payload(group="Cgroup")
    assert line_events(grouped, signature(grouped), config(), "fixture-private-secret") == []
    allowed = {**config(), "targets": ["Cgroup"]}
    assert line_events(grouped, signature(grouped), allowed, "fixture-private-secret")[0]["target"] == "Cgroup"


def test_line_webhook_durable_ack_dedup_and_body_limit(saved):
    store, identity = saved
    app = line_app(store, {identity: config()}, {identity: store.credentials(identity)})
    with TestClient(app) as client:
        raw = line_payload()
        headers = {"x-line-signature": signature(raw)}
        assert client.post(f"/line/{identity}", content=raw, headers=headers).status_code == 200
        assert client.post(f"/line/{identity}", content=raw, headers=headers).status_code == 200
        assert len(store.history(identity, USER)) == 1
        assert client.post(f"/line/{identity}", content=raw).status_code == 401
        assert client.post("/line/missing", content=raw, headers=headers).status_code == 404
        assert client.post(f"/line/{identity}", content=b"x" * (1024 * 1024 + 1)).status_code == 413
        verification = b'{"events":[]}'
        assert client.post(f"/line/{identity}", content=verification, headers={"x-line-signature": signature(verification)}).status_code == 200


def test_inbox_cursor_commit_outbox_recovery_and_draft_isolation(saved):
    store, identity = saved
    incoming = message("remote1", "target", "sender", "こんにちは")
    store.ingest(identity, [incoming], {"offset": 2})
    store.ingest(identity, [incoming], {"offset": 3})
    assert len(store.history(identity, "target")) == 1
    assert store.cursor(identity) == {"offset": 3}

    store.draft(identity, "target", "Draft")
    assert store.draft(identity, "other") == ""
    queued = store.enqueue(identity, "target", "Reply")
    sending = store.enqueue(identity, "target", "Different reply")
    store.settle(sending, "sending")
    store.recover()
    rows = {row["id"]: row for row in store.history(identity, "target")}
    assert rows[queued]["status"] == "failed"
    assert rows[sending]["status"] == "uncertain"
    assert store.queued(identity) == []
    with pytest.raises(ValueError):
        store.enqueue(identity, "target", "😀" * 951)
    with pytest.raises(ValueError):
        store.ingest(identity, [{**incoming, "remote_id": "bad", "text": None}], {"offset": 4})
    assert store.cursor(identity) == {"offset": 3}


def test_paged_history_orders_by_remote_timestamp_and_local_names_search(saved):
    store, identity = saved
    store.ingest(identity, [message("new", "target", "sender", "New", created=200)])
    store.ingest(identity, [message("old", "target", "sender", "Old", created=100)])
    assert [r["text"] for r in store.history(identity, "target")] == ["Old", "New"]
    store.label(identity, "target", "リリース確認")
    assert store.conversations(identity, "リリース")[0]["label"] == "リリース確認"


def test_gateway_exclusive_edit_lock_and_future_schema(saved):
    store, _ = saved
    first, second = MessagingGateway(store), MessagingGateway(store)
    with first.editing():
        with pytest.raises(ValueError, match="Stop the gateway"):
            with second.editing():
                pytest.fail("Two editors acquired the gateway lock")
        with pytest.raises(ValueError, match="Another Kotoba"):
            second.start()
    with second.editing():
        pass
    with store.connect() as db:
        db.execute("PRAGMA user_version=2")
    with pytest.raises(ValueError, match="newer"):
        MessagingStore(store.path.parent)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_outbound_requests_use_platform_endpoint_and_text_contract(platform):
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True, "result": {}})
    adapter = PlatformAdapter(config(platform), {"token": "fixture-token"}, httpx.MockTransport(handle))
    try:
        adapter.send(dict(id=uuid.uuid4().hex, target="target", thread="", text="Hello 日本語 <@everyone>"))
        body = json.loads(calls[0].content)
        assert calls[0].method == "POST"
        if platform == "line":
            assert calls[0].url.path == "/v2/bot/message/push"
            assert body["messages"][0]["text"].startswith("Hello 日本語")
            assert uuid.UUID(calls[0].headers["x-line-retry-key"]).version == 4
        elif platform == "discord":
            assert body["allowed_mentions"] == {"parse": []}
        elif platform == "slack":
            assert body["mrkdwn"] is False and "&lt;@everyone&gt;" in body["text"]
        else:
            assert "parse_mode" not in body
    finally:
        adapter.close()


def test_delivery_timeout_is_uncertain_and_never_leaks_token():
    def fail(request):
        raise httpx.ReadTimeout("secret-url-fixture-token", request=request)
    adapter = PlatformAdapter(config("telegram"), {"token": "fixture-token"}, httpx.MockTransport(fail))
    try:
        with pytest.raises(MessagingError) as error:
            adapter.send(dict(id=uuid.uuid4().hex, target="123", thread="", text="hello"))
        assert error.value.uncertain
        assert "fixture-token" not in str(error.value)
    finally:
        adapter.close()


def test_rate_limit_is_definite_and_preserves_retry_after():
    adapter = PlatformAdapter(config("discord"), {"token": "fixture"}, httpx.MockTransport(lambda r: httpx.Response(429, headers={"Retry-After": "120"})))
    try:
        with pytest.raises(MessagingError) as error:
            adapter.send(dict(id=uuid.uuid4().hex, target="123", thread="", text="hello"))
        assert not error.value.uncertain and error.value.retry_after == 120
    finally:
        adapter.close()


def test_telegram_filters_bots_and_users_keeps_topics_and_advances_ignored_updates():
    updates = [{"update_id": n, "message": {"message_id": n, "message_thread_id": 8, "from": {"id": user, "is_bot": bot}, "chat": {"id": -456, "type": "supergroup"}, "text": "日本語"}} for n, user, bot in [(1,123,False),(2,999,False),(3,123,True)]]
    adapter = PlatformAdapter({**config("telegram"), "targets": ["-456"]}, {"token": "fixture"}, httpx.MockTransport(lambda r: httpx.Response(200, json={"ok": True, "result": updates})))
    try:
        rows, cursor = adapter.poll({})
        assert len(rows) == 1 and rows[0]["conversation"] == "-456 / 8"
        assert cursor == {"offset": 4}
    finally:
        adapter.close()


def test_slack_pagination_preserves_watermark_until_last_page():
    pages = iter([{"ok": True, "messages": [{"ts": "1700000000.000009", "user": "U123", "text": "new"}], "response_metadata": {"next_cursor": "next"}},
                  {"ok": True, "messages": [{"ts": "1700000000.000002", "user": "U123", "text": "older"}]}])
    adapter = PlatformAdapter(config("slack"), {"token": "fixture"}, httpx.MockTransport(lambda r: httpx.Response(200, json=next(pages))))
    try:
        _, cursor = adapter.poll({"oldest": "1700000000.000001"})
        assert cursor["oldest"] == "1700000000.000001" and cursor["next"] == "next"
        _, cursor = adapter.poll(cursor)
        assert cursor == {"oldest": "1700000000.000009"}
    finally:
        adapter.close()


def test_real_line_listener_owns_port_and_releases_it(saved):
    store, identity = saved
    receiver = LineReceiver(line_app(store, {identity: config()}, {identity: store.credentials(identity)}), 0)
    raw = line_payload()
    try:
        with httpx.Client(trust_env=False) as client:
            result = client.post(f"http://127.0.0.1:{receiver.port}/line/{identity}", content=raw, headers={"x-line-signature": signature(raw)})
            assert result.status_code == 200
    finally:
        receiver.close()
    assert not receiver.thread.is_alive()


def test_worker_never_retries_uncertain_delivery(saved):
    store, identity = saved
    store.ingest(identity, [message("first", USER, USER, "Hello")])
    queued = store.enqueue(identity, USER, "Reply")
    calls = []
    class Adapter:
        platform = "telegram"
        def __init__(self, *args): pass
        def verify(self): return "Fixture"
        def close(self): calls.append("closed")
        def send(self, row):
            calls.append(row["id"])
            worker.request_stop()
            raise MessagingError("Timeout", True)
    worker = GatewayWorker(store, [{**config("telegram"), "id": identity}], 0, Adapter)
    worker.run()
    assert calls == [queued, "closed"]
    assert store.history(identity, USER)[-1]["status"] == "uncertain"


def test_unread_tracks_arrivals_even_when_history_pages_are_older(saved):
    store, identity = saved
    store.ingest(identity, [message("new", "target", "sender", "New", created=200)])
    assert store.unread() == {identity: 1}
    store.mark_read(identity, "target")
    assert store.unread() == {}
    store.ingest(identity, [message("old", "target", "sender", "Older page", created=100)])
    assert store.unread() == {identity: 1}
    store.enqueue(identity, "target", "Outgoing")
    assert store.unread() == {identity: 1}


def test_public_webhook_origin_requires_https_without_credentials_or_path():
    validate_config({**config(), "public_url": "https://tunnel.example"})
    for url in ("http://tunnel.example", "https://user:secret@tunnel.example", "https://tunnel.example/path", "https://tunnel.example?token=secret"):
        with pytest.raises(ValueError):
            validate_config({**config(), "public_url": url})
