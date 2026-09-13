"""Text-only platform adapters with explicit sender filtering and fixed API origins."""

import base64
import hashlib
import hmac
import html
import json
import time
import uuid
from decimal import Decimal
import httpx


class MessagingError(Exception):
    def __init__(self, message, uncertain=False, retry_after=30):
        super().__init__(message)
        self.uncertain = uncertain
        self.retry_after = max(1, min(float(retry_after), 3600))


def message(remote_id, target, sender, text, thread="", created=None):
    return dict(remote_id=str(remote_id), target=str(target), sender=str(sender), text=text,
                thread=str(thread), conversation=str(target) + (" / " + str(thread) if thread else ""), created=time.time() if created is None else created)


class PlatformAdapter:
    def __init__(self, config, credentials, transport=None):
        self.config, self.credentials = config, credentials
        self.platform = config["platform"]
        self.client = httpx.Client(timeout=12, follow_redirects=False, transport=transport)
        self.identity = None

    def close(self):
        self.client.close()

    def request(self, method, path, *, body=None, params=None, sending=False, headers=None):
        token = self.credentials["token"]
        origin = {"line": "https://api.line.me", "slack": "https://slack.com/api", "discord": "https://discord.com/api/v10", "telegram": "https://api.telegram.org/bot" + token}[self.platform]
        authorization = ("Bot " if self.platform == "discord" else "Bearer ") + token
        try:
            with self.client.stream(method, origin + path, params=params, json=body,
                                    headers={"Authorization": authorization, **(headers or {})}) as response:
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 4 * 1024 * 1024:
                        raise MessagingError("Platform response exceeded the size limit.", sending)
                if response.status_code == 429:
                    try:
                        wait = float(response.headers.get("Retry-After", "60"))
                    except ValueError:
                        wait = 60
                    raise MessagingError("Rate limited. Wait before trying again. / レート制限中です。しばらくお待ちください。", False, wait)
                if not 200 <= response.status_code < 300:
                    raise MessagingError(f"Platform rejected the request (HTTP {response.status_code}). Check token, permissions and destination. / 認証・権限・送信先を確認してください。", sending and response.status_code >= 500)
                value = json.loads(raw) if raw else {}
        except (httpx.HTTPError, ValueError) as error:
            raise MessagingError("Network or response error. / 通信または応答のエラーです。", sending) from None
        if self.platform in ("telegram", "slack"):
            if not isinstance(value, dict) or not value.get("ok"):
                raise MessagingError("Platform request was not accepted. Check credentials, scopes and channel access. / 認証情報・権限・チャンネルを確認してください。")
            if self.platform == "telegram":
                return value.get("result")
        return value

    def verify(self):
        endpoint = {"line": "/v2/bot/info", "telegram": "/getMe", "slack": "/auth.test", "discord": "/users/@me"}[self.platform]
        result = self.request("GET", endpoint)
        if not isinstance(result, dict):
            raise MessagingError("Unexpected identity response")
        self.identity = str(result.get("id") or result.get("user_id") or result.get("userId") or "")
        if self.platform == "telegram":
            webhook = self.request("GET", "/getWebhookInfo")
            if webhook.get("url"):
                raise MessagingError("This Telegram bot has an active webhook. Remove it in your existing deployment before using polling; Kotoba will not replace it automatically.")
        return str(result.get("displayName") or result.get("username") or result.get("user") or self.identity)

    def poll(self, cursor):
        allowed = set(self.config["users"])
        if self.platform == "line":
            return [], cursor
        if self.platform == "telegram":
            updates = self.request("POST", "/getUpdates", body={"offset": cursor.get("offset", 0), "timeout": 5, "limit": 100, "allowed_updates": ["message"]})
            items, offset = [], cursor.get("offset", 0)
            for update in updates:
                offset = max(offset, int(update["update_id"]) + 1)
                row = update.get("message", {})
                author, chat = row.get("from", {}), row.get("chat", {})
                sender, target = str(author.get("id", "")), str(chat.get("id", ""))
                if author.get("is_bot") or sender not in allowed:
                    continue
                if chat.get("type") != "private" and target not in self.config["targets"]:
                    continue
                if isinstance(row.get("text"), str):
                    items.append(message(target + ":" + str(row["message_id"]), target, sender, row["text"], row.get("message_thread_id", ""), row.get("date", time.time())))
            return items, {"offset": offset}
        channel = self.config["channel"]
        if self.platform == "discord":
            if not cursor:
                rows = self.request("GET", f"/channels/{channel}/messages", params={"limit": 1})
                return [], {"after": str(rows[0]["id"]) if rows else "0"}
            params = {"limit": 100, "before": cursor["before"]} if cursor.get("before") else {"limit": 100, "after": cursor["after"]}
            batch = self.request("GET", f"/channels/{channel}/messages", params=params)
            rows = [row for row in batch if int(row["id"]) > int(cursor["after"])]
            items = [message(row["id"], channel, row["author"]["id"], row["content"], created=((int(row["id"]) >> 22) + 1420070400000) / 1000) for row in reversed(rows)
                     if not row.get("author", {}).get("bot") and str(row.get("author", {}).get("id")) in allowed and isinstance(row.get("content"), str) and row["content"]]
            newest = str(max([int(cursor.get("newest", cursor["after"]))] + [int(r["id"]) for r in rows]))
            state = {"after": cursor["after"], "newest": newest, "before": str(min(int(r["id"]) for r in rows))} if len(batch) == 100 and len(rows) == 100 else {"after": newest}
            return items, state
        # Keep the lower watermark until every Slack page has been persisted.
        state = dict(cursor) if cursor else {"oldest": str(time.time())}
        params = {"channel": channel, "oldest": state["oldest"], "limit": 15, "inclusive": False}
        if state.get("next"):
            params["cursor"] = state["next"]
        result = self.request("GET", "/conversations.history", params=params)
        rows = result.get("messages", [])
        newest = max([state.get("newest", state["oldest"])] + [r["ts"] for r in rows], key=Decimal)
        items = [message(row["ts"], channel, row["user"], html.unescape(row["text"]), created=float(row["ts"])) for row in reversed(rows)
                 if row.get("user") in allowed and not row.get("bot_id") and not row.get("subtype") and isinstance(row.get("text"), str)]
        next_page = result.get("response_metadata", {}).get("next_cursor", "")
        return items, ({"oldest": state["oldest"], "newest": newest, "next": next_page} if next_page else {"oldest": newest})

    def send(self, row):
        target, thread, text = row["target"], row["thread"], row["text"]
        if self.platform == "line":
            self.request("POST", "/v2/bot/message/push", body={"to": target, "messages": [{"type": "text", "text": text}]}, headers={"X-Line-Retry-Key": str(uuid.UUID(row["id"]))}, sending=True)
        elif self.platform == "telegram":
            body = {"chat_id": target, "text": text, "link_preview_options": {"is_disabled": True}}
            if thread:
                body["message_thread_id"] = int(thread)
            self.request("POST", "/sendMessage", body=body, sending=True)
        elif self.platform == "slack":
            body = {"channel": target, "text": html.escape(text, quote=False), "mrkdwn": False, "unfurl_links": False, "unfurl_media": False}
            self.request("POST", "/chat.postMessage", body=body, sending=True)
        else:
            self.request("POST", f"/channels/{target}/messages", body={"content": text, "allowed_mentions": {"parse": []}}, sending=True)


def line_events(raw, signature, config, secret):
    expected = base64.b64encode(hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()
    if not signature or not hmac.compare_digest(expected, signature):
        raise PermissionError("Invalid LINE signature")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("Invalid LINE payload")
    items = []
    for event in payload["events"]:
        source = event.get("source", {})
        sender = source.get("userId", "")
        target = source.get("groupId") or source.get("roomId") or sender
        if sender not in config["users"] or (source.get("type") != "user" and target not in config["targets"]):
            continue
        row = event.get("message", {})
        if event.get("type") == "message" and row.get("type") == "text" and isinstance(row.get("text"), str):
            items.append(message(row["id"], target, sender, row["text"], created=event.get("timestamp", time.time() * 1000) / 1000))
    return items
