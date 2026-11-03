"""Local accounts, sessions and private conversation storage."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "app.db"
SESSION_SECONDS = 7 * 24 * 3600


@contextmanager
def connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
          password_hash BLOB NOT NULL, salt BLOB NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT NOT NULL CHECK(role IN ('user','assistant')),
          content TEXT NOT NULL, mode TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
        """)


def register(username: str, password: str) -> dict:
    if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,31}", username):
        raise ValueError("账号须为 3–32 位，以字母开头，仅含字母、数字或下划线")
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        raise ValueError("密码须为 8–128 个字符")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    try:
        with connection() as db:
            cur = db.execute("INSERT INTO users(username,password_hash,salt,created_at) VALUES(?,?,?,?)", (username, digest, salt, int(time.time())))
            return {"id": cur.lastrowid, "username": username}
    except sqlite3.IntegrityError as error:
        raise ValueError("账号已存在") from error


def guest_user() -> dict:
    """Return the local preview identity without exposing a shared password."""
    with connection() as db:
        row = db.execute("SELECT id,username FROM users WHERE username='guest'").fetchone()
    if row:
        return dict(row)
    try:
        return register("guest", secrets.token_urlsafe(32))
    except ValueError:
        with connection() as db:
            row = db.execute("SELECT id,username FROM users WHERE username='guest'").fetchone()
        return dict(row)


def verify(username: str, password: str) -> dict | None:
    if not isinstance(username, str) or not isinstance(password, str):
        return None
    with connection() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        return None
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), row["salt"], 310_000)
    if not hmac.compare_digest(digest, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"]}


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connection() as db:
        db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, int(time.time()) + SESSION_SECONDS))
    return token


def get_user(token: str | None) -> dict | None:
    if not token:
        return None
    with connection() as db:
        row = db.execute("SELECT u.id,u.username FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
    return dict(row) if row else None


def delete_session(token: str | None):
    if token:
        with connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def list_conversations(user_id: int) -> list[dict]:
    with connection() as db:
        rows = db.execute("SELECT id,title,updated_at FROM conversations WHERE user_id=? ORDER BY updated_at DESC,id DESC LIMIT 100", (user_id,)).fetchall()
    return [dict(row) for row in rows]


def get_conversation(user_id: int, conversation_id: int) -> dict | None:
    with connection() as db:
        row = db.execute("SELECT id,title,updated_at FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone()
        if not row:
            return None
        messages = db.execute("SELECT id,role,content,mode,created_at FROM messages WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
    return {**dict(row), "messages": [dict(message) for message in messages]}


def save_exchange(user_id: int, conversation_id: int | None, question: str, answer: str, mode: str) -> dict:
    now = int(time.time())
    with connection() as db:
        if conversation_id is None:
            cur = db.execute("INSERT INTO conversations(user_id,title,created_at,updated_at) VALUES(?,?,?,?)", (user_id, question[:32], now, now))
            conversation_id = cur.lastrowid
        else:
            row = db.execute("SELECT id FROM conversations WHERE id=? AND user_id=?", (conversation_id, user_id)).fetchone()
            if not row:
                raise ValueError("对话不存在")
        db.execute("INSERT INTO messages(conversation_id,role,content,mode,created_at) VALUES(?,?,?,?,?)", (conversation_id, "user", question, "", now))
        db.execute("INSERT INTO messages(conversation_id,role,content,mode,created_at) VALUES(?,?,?,?,?)", (conversation_id, "assistant", answer, mode, now))
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conversation_id))
    return get_conversation(user_id, conversation_id)
