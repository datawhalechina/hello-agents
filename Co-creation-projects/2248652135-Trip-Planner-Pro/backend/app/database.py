"""数据库管理 - SQLite"""
import sqlite3
import os
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "trip_planner.db"


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trip_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                city TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                travel_days INTEGER NOT NULL DEFAULT 0,
                preferences TEXT DEFAULT '',
                traveler_group TEXT DEFAULT '',
                plan_data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tokens_user ON auth_tokens(user_id);
            CREATE INDEX IF NOT EXISTS idx_tokens_token ON auth_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_history_user ON trip_history(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ============ 用户管理 ============

def get_user_by_id(user_id: int) -> dict:
    """通过ID获取用户信息"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def hash_password(password: str, salt: str = None) -> tuple:
    """密码加盐哈希,返回 (hash, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


def create_user(username: str, password: str) -> dict:
    """创建用户,返回用户信息"""
    conn = get_db()
    try:
        pwd_hash, salt = hash_password(password)
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, pwd_hash, salt)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "username": username}
    except sqlite3.IntegrityError:
        raise ValueError("用户名已存在")
    finally:
        conn.close()


def verify_user(username: str, password: str) -> dict:
    """验证用户登录,返回用户信息或None"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, username, password_hash, salt FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        if not row:
            return None
        pwd_hash, _ = hash_password(password, row["salt"])
        if pwd_hash != row["password_hash"]:
            return None
        return {"id": row["id"], "username": row["username"]}
    finally:
        conn.close()


# ============ Token管理 ============

def create_token(user_id: int) -> str:
    """创建登录token"""
    token = secrets.token_hex(32)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO auth_tokens (user_id, token) VALUES (?, ?)",
            (user_id, token)
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_user_by_token(token: str) -> dict:
    """通过token获取用户信息"""
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT u.id, u.username FROM users u
               JOIN auth_tokens t ON t.user_id = u.id
               WHERE t.token = ?""",
            (token,)
        ).fetchone()
        if row:
            return {"id": row["id"], "username": row["username"]}
        return None
    finally:
        conn.close()


def delete_token(token: str):
    """删除token(登出)"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ============ 历史记录管理 ============

def save_trip_history(user_id: int, city: str, start_date: str, end_date: str,
                      travel_days: int, preferences: str, traveler_group: str,
                      plan_data: str) -> int:
    """保存行程到历史记录"""
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO trip_history
               (user_id, city, start_date, end_date, travel_days, preferences, traveler_group, plan_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, city, start_date, end_date, travel_days, preferences, traveler_group, plan_data)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_trip_history(user_id: int, limit: int = 20, offset: int = 0) -> list:
    """列出用户的历史记录"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, city, start_date, end_date, travel_days, preferences, traveler_group, created_at
               FROM trip_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_trip_history(history_id: int, user_id: int) -> dict:
    """获取单条历史记录详情"""
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT * FROM trip_history WHERE id = ? AND user_id = ?""",
            (history_id, user_id)
        ).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def delete_trip_history(history_id: int, user_id: int) -> bool:
    """删除历史记录"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM trip_history WHERE id = ? AND user_id = ?",
            (history_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============ 聊天会话管理 ============

def init_chat_tables():
    """初始化聊天相关表（增量迁移）"""
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
        """)
        conn.commit()
    finally:
        conn.close()


def create_chat_session(user_id: int, title: str = "新对话") -> dict:
    """创建聊天会话"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (user_id, title)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "title": title}
    finally:
        conn.close()


def list_chat_sessions(user_id: int) -> list:
    """列出用户的所有聊天会话（按更新时间倒序）"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, title, created_at, updated_at
               FROM chat_sessions
               WHERE user_id = ?
               ORDER BY updated_at DESC""",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_chat_session(session_id: int, user_id: int) -> dict:
    """获取单个聊天会话"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_chat_session_title(session_id: int, title: str) -> bool:
    """更新会话标题"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (title, session_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_chat_session(session_id: int, user_id: int) -> bool:
    """删除聊天会话（级联删除消息）"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# ============ 聊天消息管理 ============

def add_chat_message(session_id: int, role: str, content: str) -> dict:
    """添加聊天消息，并更新会话的 updated_at"""
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = datetime('now','localtime') WHERE id = ?",
            (session_id,)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "session_id": session_id, "role": role, "content": content}
    finally:
        conn.close()


def get_chat_messages(session_id: int) -> list:
    """获取会话的所有消息（按时间正序）"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT id, role, content, created_at
               FROM chat_messages
               WHERE session_id = ?
               ORDER BY id ASC""",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
