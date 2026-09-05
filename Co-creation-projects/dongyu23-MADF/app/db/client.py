import os
import libsql_client
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
import logging
import json
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PostgresTransaction:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor(cursor_factory=RealDictCursor)

    def execute(self, query, params=None):
        # Convert ? to %s for psycopg2
        query = query.replace('?', '%s')
        self.cursor.execute(query, params)
        return self.cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()

class PostgresClient:
    def __init__(self, url):
        self.url = url
        self.conn = psycopg2.connect(url)
        self.conn.autocommit = True

    def execute(self, query, params=None):
        # Convert ? to %s for psycopg2
        query = query.replace('?', '%s')
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            # If it's a SELECT or RETURNING, fetch results
            if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper():
                return cur.fetchall()
            return cur

    def transaction(self):
        self.conn.autocommit = False
        return PostgresTransaction(self.conn)
    
    def close(self):
        self.conn.close()

class RetryingTransaction:
    """Wrapper for libsql transaction to add retry logic"""
    def __init__(self, tx):
        self._tx = tx
        
    def execute(self, stmt, args=None):
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                return self._tx.execute(stmt, args)
            except Exception as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Database locked in transaction, retrying in {delay:.2f}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise e
    
    def commit(self):
        if hasattr(self._tx, 'commit'):
            return self._tx.commit()
            
    def __getattr__(self, name):
        return getattr(self._tx, name)

class RetryingLibsqlClient:
    """Wrapper around libsql_client to add retry logic for locking errors"""
    def __init__(self, client):
        self._client = client

    def execute(self, stmt, args=None):
        max_retries = 5
        base_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                return self._client.execute(stmt, args)
            except Exception as e:
                error_msg = str(e).lower()
                if "database is locked" in error_msg:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) # Exponential backoff
                        logger.warning(f"Database locked, retrying in {delay:.2f}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                # If not locked error or retries exhausted, raise
                raise e

    @contextmanager
    def transaction(self):
        # We need to wrap the yielded transaction object
        # self._client.transaction() returns a context manager itself
        with self._client.transaction() as tx:
            yield RetryingTransaction(tx)
        
    def close(self):
        return self._client.close()
        
    def __getattr__(self, name):
        return getattr(self._client, name)

class Database:
    def __init__(self):
        self.url = settings.DATABASE_URL
        self.auth_token = settings.TURSO_AUTH_TOKEN
        self.is_postgres = self.url.startswith("postgresql://") or self.url.startswith("postgres://")
        self.is_remote = self.url.startswith("libsql://") or self.url.startswith("https://")
        
    def get_connection(self):
        if self.is_postgres:
            return PostgresClient(self.url)
            
        token = self.auth_token if self.is_remote else None
        
        # Ensure directory exists for local file
        if not self.is_remote and self.url.startswith("file:"):
            db_path = self.url.replace("file:", "")
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir and not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info(f"Created database directory: {db_dir}")
                except OSError as e:
                    logger.warning(f"Failed to create database directory: {e}")

        # 使用 create_client_sync 创建连接
        # LibSQL client automatically creates the file if it doesn't exist for local file URLs
        try:
            client = libsql_client.create_client_sync(
                url=self.url,
                auth_token=token
            )
        except Exception as e:
            logger.error(f"Failed to create database client: {e}")
            # Fallback or retry logic could go here, but for now just re-raise
            raise e
        
        # --- SQLite WAL 模式与性能优化 ---
        if not self.is_remote and not self.is_postgres:
            try:
                # 启用 WAL 模式：大幅提升并发读写性能
                client.execute("PRAGMA journal_mode = WAL")
                # 设置同步模式为 NORMAL：在 WAL 模式下既安全又快
                client.execute("PRAGMA synchronous = NORMAL")
                # 增加缓存大小
                client.execute("PRAGMA cache_size = -10000")
                # 启用外键约束
                client.execute("PRAGMA foreign_keys = ON")
                # 设置忙碌超时，防止 database is locked 错误 (增加到 30秒)
                client.execute("PRAGMA busy_timeout = 30000")
            except Exception as e:
                logger.warning(f"Failed to set SQLite PRAGMA: {e}")

        # Wrap with retry logic
        if not self.is_remote and not self.is_postgres:
            return RetryingLibsqlClient(client)
            
        return client

    def init_db(self, schema_path="app/db/schema.sql"):
        """初始化数据库结构"""
        # 如果是 Postgres，跳过 schema.sql，假设使用 Alembic 或 schema_pg.sql
        if self.is_postgres:
            logger.info("PostgreSQL detected, skipping schema.sql init. Use Alembic or schema_pg.sql.")
            return

        if not os.path.exists(schema_path):
            logger.warning(f"Schema file not found: {schema_path}")
            return

        conn = self.get_connection()
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                script = f.read()
                # LibSQL client executescript equivalent: split by ;
                # Or use execute for single statement.
                # libsql-client-py execute() might not support multiple statements.
                # Let's split manually.
                statements = [s.strip() for s in script.split(';') if s.strip()]
                for stmt in statements:
                    conn.execute(stmt)

                # Existing local databases predate persisted scheduler flags.
                # Keep startup migration idempotent because schema.sql only creates
                # tables when they do not exist.
                if not self.is_remote and not self.is_postgres:
                    user_columns = fetch_all(conn.execute("PRAGMA table_info(users)"))
                    if "email" not in {column.name for column in user_columns}:
                        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
                        conn.execute(
                            "CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON users(email)"
                        )

                    columns = fetch_all(conn.execute("PRAGMA table_info(forums)"))
                    if "ablation_flags" not in {column.name for column in columns}:
                        conn.execute(
                            "ALTER TABLE forums ADD COLUMN ablation_flags TEXT DEFAULT '{}'"
                        )

                    # Older versions accepted whitespace-only persona names.
                    # Repair them before response validation is applied so an
                    # upgraded database remains readable.
                    conn.execute(
                        """
                        UPDATE personas
                        SET name = '未命名智能体 #' || id
                        WHERE name IS NULL OR TRIM(name) = ''
                        """
                    )
                    
            logger.info("Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
        finally:
            conn.close()

db_manager = Database()

def get_db():
    db = db_manager.get_connection()
    try:
        yield db
    finally:
        db.close()

# Helper for Row Objects (SQLite returns rows, Postgres returns dicts)
class RowObject:
    def __init__(self, data):
        self.__dict__.update(data)
        
def fetch_one(rs):
    if rs is None:
        return None
    # If it's a list (Postgres or cached), return first
    if isinstance(rs, list):
        return RowObject(rs[0]) if rs else None
    # LibSQL ResultSet
    if hasattr(rs, 'rows'):
        return RowObject(dict(zip(rs.columns, rs.rows[0]))) if rs.rows else None
    # Psycopg2 cursor
    if hasattr(rs, 'fetchone'):
        row = rs.fetchone()
        return RowObject(row) if row else None
    return None

def fetch_all(rs):
    if rs is None:
        return []
    if isinstance(rs, list):
        return [RowObject(r) for r in rs]
    if hasattr(rs, 'rows'):
        return [RowObject(dict(zip(rs.columns, row))) for row in rs.rows]
    if hasattr(rs, 'fetchall'):
        return [RowObject(row) for row in rs.fetchall()]
    return []

@contextmanager
def db_transaction(db):
    """
    Unified transaction context manager.
    - If `db` is a connection (has `.transaction()`), starts a new transaction.
    - If `db` is already a transaction object, reuses it (nested transaction support/no-op).
    """
    if hasattr(db, 'transaction') and callable(db.transaction):
        with db.transaction() as tx:
            yield tx
    else:
        # Assume db is already a transaction object or behaves like one
        # For LibSQL/SQLite, nested transactions are not supported directly with SAVEPOINT in this wrapper yet
        # So we just yield the existing transaction object.
        yield db

def db_execute_commit(db, query, params=None):
    """
    Helper to execute a query and force commit if applicable.
    Useful for one-off write operations to ensure persistence in SQLite WAL mode.
    """
    if hasattr(db, 'transaction') and callable(db.transaction):
        with db.transaction() as tx:
            rs = tx.execute(query, params)
            # Force commit for SQLite if wrapper doesn't auto-commit on exit (it usually does)
            # But let's be safe for our specific issue
            if hasattr(tx, 'commit'):
                tx.commit()
            elif hasattr(db, 'commit'):
                db.commit()
            return rs
    else:
        # Already in a transaction, just execute
        return db.execute(query, params)
