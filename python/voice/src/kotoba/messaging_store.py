"""Durable messaging inbox, explicit outbox, and Windows user-bound credentials."""

from contextlib import contextmanager
import ctypes
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid
from urllib.parse import urlsplit

PLATFORMS = ("line", "slack", "discord", "telegram")
SCHEMA_VERSION = 1


def protect(data: bytes, decrypt=False):
    if sys.platform != "win32":
        raise ValueError("Messaging credential storage currently requires Windows. / 認証情報の保存には Windows が必要です。")
    class Blob(ctypes.Structure):
        _fields_ = [("size", ctypes.c_ulong), ("data", ctypes.c_void_p)]
    buffer = ctypes.create_string_buffer(data)
    source, target = Blob(len(data), ctypes.cast(buffer, ctypes.c_void_p)), Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(Blob)]
    function.restype = ctypes.c_int
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ValueError("Windows could not unlock messaging credentials. / Windows が認証情報を読み込めませんでした。")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def validate_config(config):
    if config.get("platform") not in PLATFORMS:
        raise ValueError("Unknown messaging platform")
    for field in ("name", "channel", "provider", "model"):
        if not isinstance(config.get(field), str) or len(config[field]) > 250:
            raise ValueError(f"Invalid {field}")
    for field in ("users", "targets"):
        if not isinstance(config.get(field), list) or len(config[field]) > 100 or any(not isinstance(s, str) or len(s) > 100 for s in config[field]):
            raise ValueError(f"Invalid {field}")
    pattern = {"line": r"U[0-9a-fA-F]{32}", "slack": r"[UW][A-Z0-9]+", "discord": r"[0-9]{1,25}", "telegram": r"[0-9]{1,25}"}[config["platform"]]
    if not config["users"] or any(not re.fullmatch(pattern, value) for value in config["users"]):
        raise ValueError("Enter valid allowed user IDs; empty lists never allow public access. / 許可するユーザー ID を入力してください。空欄では公開アクセスを許可しません。")
    if config["platform"] in ("slack", "discord"):
        pattern = r"[CGD][A-Z0-9]+" if config["platform"] == "slack" else r"[0-9]{1,25}"
        if not re.fullmatch(pattern, config["channel"]):
            raise ValueError("Enter the channel ID / チャンネル ID を入力してください")
    if config.get("language") not in ("auto", "en", "ja", "bilingual") or type(config.get("enabled")) is not bool:
        raise ValueError("Invalid language or enabled state")
    public_url = config.get("public_url", "")
    if not isinstance(public_url, str) or len(public_url) > 2000:
        raise ValueError("Invalid public webhook origin")
    if public_url:
        parsed = urlsplit(public_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Use an HTTPS origin without a path, credentials or query. / パス・認証情報・クエリを含まない HTTPS の接続先を入力してください。")


class MessagingStore:
    def __init__(self, home: Path):
        home.mkdir(parents=True, exist_ok=True)
        self.path = home / "messaging.sqlite3"
        with self.connect() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] > SCHEMA_VERSION:
                raise ValueError("Messaging data requires a newer Kotoba Studio.")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY, config TEXT NOT NULL, secret BLOB NOT NULL, cursor TEXT NOT NULL DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, connection TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
                    remote_id TEXT, conversation TEXT NOT NULL, target TEXT NOT NULL, thread TEXT NOT NULL, sender TEXT NOT NULL,
                    text TEXT NOT NULL, direction TEXT NOT NULL, status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', created REAL NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS remote_message ON messages(connection,remote_id) WHERE remote_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS conversation_messages ON messages(connection,conversation,created);
                CREATE TABLE IF NOT EXISTS drafts(connection TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
                    conversation TEXT NOT NULL, text TEXT NOT NULL, PRIMARY KEY(connection,conversation));
                CREATE TABLE IF NOT EXISTS conversation_labels(connection TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
                    conversation TEXT NOT NULL, label TEXT NOT NULL, PRIMARY KEY(connection,conversation));
                CREATE TABLE IF NOT EXISTS seen(connection TEXT NOT NULL REFERENCES connections(id) ON DELETE CASCADE,
                    conversation TEXT NOT NULL, last_rowid INTEGER NOT NULL, PRIMARY KEY(connection,conversation));
            """)
            db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def configs(self):
        with self.connect() as db:
            return [dict(json.loads(r["config"]), id=r["id"]) for r in db.execute("SELECT * FROM connections ORDER BY rowid")]

    def save_config(self, identity, config, token="", secret=""):
        validate_config(config)
        if len(token) > 8192 or len(secret) > 8192:
            raise ValueError("Credential value is too long")
        identity = identity or uuid.uuid4().hex
        with self.connect() as db:
            old = db.execute("SELECT secret FROM connections WHERE id=?", (identity,)).fetchone()
            values = json.loads(protect(old[0], True)) if old else {}
            values.update({k: v for k, v in {"token": token.strip(), "secret": secret.strip()}.items() if v})
            if not values.get("token") or (config["platform"] == "line" and not values.get("secret")):
                raise ValueError("Supply the required credentials / 必要な認証情報を入力してください")
            encrypted = protect(json.dumps(values).encode())
            db.execute("INSERT INTO connections(id,config,secret) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET config=excluded.config,secret=excluded.secret",
                       (identity, json.dumps(config, ensure_ascii=False), encrypted))
        return identity

    def credentials(self, identity):
        with self.connect() as db:
            row = db.execute("SELECT secret FROM connections WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise ValueError("Connection was removed")
        return json.loads(protect(row[0], True))

    def cursor(self, identity):
        with self.connect() as db:
            return json.loads(db.execute("SELECT cursor FROM connections WHERE id=?", (identity,)).fetchone()[0])

    def ingest(self, identity, messages, cursor=None):
        with self.connect() as db:
            for message in messages:
                if not all(isinstance(message.get(k), str) for k in ("remote_id", "conversation", "target", "thread", "sender", "text")) or len(message["text"]) > 32000:
                    raise ValueError("Invalid incoming message")
                created = message.get("created", time.time())
                if not isinstance(created, (int, float)) or not math.isfinite(created) or created < 0:
                    raise ValueError("Invalid message timestamp")
                db.execute("INSERT OR IGNORE INTO messages(id,connection,remote_id,conversation,target,thread,sender,text,direction,status,created) VALUES (?,?,?,?,?,?,?,?, 'in','received',?)",
                    (uuid.uuid4().hex, identity, message["remote_id"], message["conversation"], message["target"], message["thread"], message["sender"], message["text"], created))
            if cursor is not None:
                db.execute("UPDATE connections SET cursor=? WHERE id=?", (json.dumps(cursor), identity))

    def conversations(self, identity, query=""):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT m.conversation,COALESCE(l.label,m.conversation) AS label,MAX(m.created) AS updated,COUNT(*) AS count FROM messages m LEFT JOIN conversation_labels l ON m.connection=l.connection AND m.conversation=l.conversation WHERE m.connection=? AND (instr(lower(m.text),lower(?))>0 OR instr(lower(COALESCE(l.label,'')),lower(?))>0) GROUP BY m.conversation ORDER BY updated DESC", (identity, query, query))]

    def label(self, identity, conversation, text):
        if not text.strip() or len(text) > 100:
            raise ValueError("Use a conversation name between 1 and 100 characters.")
        with self.connect() as db:
            db.execute("INSERT INTO conversation_labels VALUES (?,?,?) ON CONFLICT(connection,conversation) DO UPDATE SET label=excluded.label", (identity, conversation, text.strip()))

    def unread(self):
        with self.connect() as db:
            return {row["connection"]: row["count"] for row in db.execute("SELECT m.connection,COUNT(*) AS count FROM messages m LEFT JOIN seen s ON m.connection=s.connection AND m.conversation=s.conversation WHERE m.direction='in' AND m.rowid>COALESCE(s.last_rowid,0) GROUP BY m.connection")}

    def mark_read(self, identity, conversation):
        with self.connect() as db:
            latest = db.execute("SELECT COALESCE(MAX(rowid),0) FROM messages WHERE connection=? AND conversation=?", (identity, conversation)).fetchone()[0]
            db.execute("INSERT INTO seen VALUES (?,?,?) ON CONFLICT(connection,conversation) DO UPDATE SET last_rowid=excluded.last_rowid", (identity, conversation, latest))

    def history(self, identity, conversation):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM messages WHERE connection=? AND conversation=? ORDER BY created DESC,rowid DESC LIMIT 200", (identity, conversation)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def draft(self, identity, conversation, text=None):
        with self.connect() as db:
            if text is not None:
                if len(text) > 32000:
                    raise ValueError("Draft too large")
                db.execute("INSERT INTO drafts VALUES (?,?,?) ON CONFLICT(connection,conversation) DO UPDATE SET text=excluded.text", (identity, conversation, text))
            row = db.execute("SELECT text FROM drafts WHERE connection=? AND conversation=?", (identity, conversation)).fetchone()
        return row[0] if row else ""

    def enqueue(self, identity, conversation, text):
        if not text.strip() or len(text.encode("utf-16-le")) // 2 > 1900:
            raise ValueError("Replies must contain 1–1900 UTF-16 units. Shorten the draft before sending. / 返信を 1900 UTF-16 単位以内にしてください。")
        rows = self.history(identity, conversation)
        if not rows:
            raise ValueError("Select a received conversation first")
        source = rows[-1]
        message_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO messages(id,connection,conversation,target,thread,sender,text,direction,status,created) VALUES (?,?,?,?,?,?,?,'out','queued',?)",
                       (message_id, identity, conversation, source["target"], source["thread"], "Kotoba", text, time.time()))
        return message_id

    def queued(self, identity):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM messages WHERE connection=? AND status='queued' ORDER BY created", (identity,))]

    def settle(self, message_id, status, error=""):
        if status not in ("sending", "sent", "failed", "uncertain"):
            raise ValueError("Invalid delivery status")
        with self.connect() as db:
            db.execute("UPDATE messages SET status=?,error=? WHERE id=?", (status, error, message_id))

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE messages SET status='uncertain',error='Interrupted during delivery; check the remote conversation before sending again.' WHERE status='sending'")
            db.execute("UPDATE messages SET status='failed',error='Gateway stopped before delivery. No automatic resend.' WHERE status='queued'")

    def delete(self, identity):
        with self.connect() as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DELETE FROM connections WHERE id=?", (identity,))
