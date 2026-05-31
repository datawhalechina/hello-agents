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

            CREATE INDEX IF NOT EXISTS idx_tokens_user ON auth_tokens(user_id);
            CREATE INDEX IF NOT EXISTS idx_tokens_token ON auth_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_history_user ON trip_history(user_id);
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
