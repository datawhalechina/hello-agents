"""数据库查询工具

提供安全的数据库查询功能，支持多种数据库连接。
"""

from typing import Dict, Any, Optional
import time
import sqlite3
from contextlib import contextmanager


@contextmanager
def get_connection(connection_string: Optional[str] = None):
    """获取数据库连接上下文管理器

    Args:
        connection_string: 数据库连接字符串
            - 普通的文件路径，如 "path/to/db.sqlite"
            - sqlite:///path/to/db.sqlite
            - :memory: 内存数据库
            - 空值使用内存数据库
    """
    conn = None
    try:
        if connection_string:
            if connection_string.startswith("sqlite:///"):
                db_path = connection_string.replace("sqlite:///", "")
            elif connection_string == ":memory:":
                db_path = ":memory:"
            else:
                db_path = connection_string
            conn = sqlite3.connect(db_path)
        else:
            conn = sqlite3.connect(":memory:")
        yield conn
    finally:
        if conn:
            conn.close()


def query_database(
    sql: str, connection_string: Optional[str] = None, limit: int = 1000
) -> Dict[str, Any]:
    """执行数据库查询

    Args:
        sql: SQL 查询语句（仅支持 SELECT）
        connection_string: 数据库连接字符串
            - 普通文件路径，如 "path/to/db.sqlite"
            - sqlite:///path/to/db.sqlite
            - :memory: 内存数据库
            - 空值使用内存数据库
        limit: 结果集最大行数

    Returns:
        查询结果字典，包含 columns, rows, row_count, execution_time_ms
    """
    start_time = time.time()

    if not sql.strip().upper().startswith("SELECT"):
        return {
            "success": False,
            "error": "Only SELECT queries are allowed for security reasons",
        }

    if limit <= 0:
        return {"success": False, "error": "Limit must be positive"}

    safe_sql = sql.strip()
    if ";" in safe_sql[:-1] if safe_sql.endswith(";") else ";" in safe_sql:
        return {"success": False, "error": "Multiple statements are not allowed"}

    try:
        with get_connection(connection_string) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            safe_sql = f"{safe_sql.rstrip(';')} LIMIT {limit}"
            cursor.execute(safe_sql)

            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            rows = [dict(row) for row in cursor.fetchall()]
            row_count = len(rows)

            execution_time_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "execution_time_ms": round(execution_time_ms, 2),
                "sql": sql,
            }
    except sqlite3.Error as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


def init_sample_database(connection_string: Optional[str] = None) -> Dict[str, Any]:
    """初始化示例数据库（用于测试）

    Args:
        connection_string: 数据库连接字符串

    Returns:
        初始化结果
    """
    sample_data_sql = """
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY,
        month TEXT NOT NULL,
        region TEXT NOT NULL,
        product TEXT NOT NULL,
        revenue REAL NOT NULL,
        quantity INTEGER NOT NULL
    );
    
    INSERT OR REPLACE INTO sales (month, region, product, revenue, quantity) VALUES
        ('2024-01', 'North', 'Product A', 15000.0, 150),
        ('2024-01', 'South', 'Product A', 12000.0, 120),
        ('2024-01', 'North', 'Product B', 18000.0, 90),
        ('2024-02', 'South', 'Product A', 14000.0, 140),
        ('2024-02', 'North', 'Product B', 20000.0, 100),
        ('2024-02', 'South', 'Product B', 16000.0, 80),
        ('2024-03', 'North', 'Product A', 17000.0, 170),
        ('2024-03', 'South', 'Product A', 13000.0, 130),
        ('2024-03', 'North', 'Product B', 22000.0, 110);
    """

    try:
        with get_connection(connection_string) as conn:
            cursor = conn.cursor()
            for statement in sample_data_sql.strip().split(";"):
                if statement.strip():
                    cursor.execute(statement)
            conn.commit()
            return {"success": True, "message": "Sample database initialized"}
    except Exception as e:
        return {"success": False, "error": str(e)}
