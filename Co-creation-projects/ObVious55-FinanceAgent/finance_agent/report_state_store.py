from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import pymysql
except ImportError:  # pragma: no cover - optional production dependency.
    pymysql = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in tests.
    load_dotenv = None


TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(slots=True)
class MySQLStateStore:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> MySQLStateStore | None:
        load_project_env()
        if os.getenv("REPORT_STATE_MYSQL_ENABLED", "").lower() not in TRUE_VALUES:
            return None
        return cls(
            host=os.getenv("REPORT_STATE_MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("REPORT_STATE_MYSQL_PORT", "3307")),
            database=os.getenv("REPORT_STATE_MYSQL_DATABASE", "finance_agent"),
            user=os.getenv("REPORT_STATE_MYSQL_USER", "finance_user"),
            password=os.getenv("REPORT_STATE_MYSQL_PASSWORD", "finance_password"),
        )

    def available(self) -> bool:
        return pymysql is not None

    def save_snapshot(
        self,
        *,
        run_id: str,
        business_task: str,
        thread_id: str,
        step_no: int,
        snapshot_name: str,
        current_node: str,
        next_node: str | None,
        policy_version: str | None,
        schema_version: str,
        state_json: str,
        patch_json: str,
        evidence_refs_json: str,
        status: str,
        parent_snapshot_id: int | None,
        state_hash: str,
        error_message: str | None = None,
    ) -> int:
        if pymysql is None:
            raise RuntimeError("Missing dependency: install PyMySQL to persist state snapshots in MySQL.")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(SNAPSHOT_TABLE_SQL)
                cursor.execute(
                    """
                    INSERT INTO agent_state_snapshot (
                        run_id,
                        business_task,
                        thread_id,
                        step_no,
                        snapshot_name,
                        current_node,
                        next_node,
                        policy_version,
                        schema_version,
                        state_json,
                        patch_json,
                        evidence_refs_json,
                        status,
                        parent_snapshot_id,
                        state_hash,
                        error_message
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        CAST(%s AS JSON), CAST(%s AS JSON), CAST(%s AS JSON),
                        %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        business_task = VALUES(business_task),
                        current_node = VALUES(current_node),
                        next_node = VALUES(next_node),
                        policy_version = VALUES(policy_version),
                        schema_version = VALUES(schema_version),
                        state_json = VALUES(state_json),
                        patch_json = VALUES(patch_json),
                        evidence_refs_json = VALUES(evidence_refs_json),
                        status = VALUES(status),
                        parent_snapshot_id = VALUES(parent_snapshot_id),
                        state_hash = VALUES(state_hash),
                        error_message = VALUES(error_message),
                        updated_at = CURRENT_TIMESTAMP(3),
                        id = LAST_INSERT_ID(id)
                    """,
                    (
                        run_id,
                        business_task,
                        thread_id,
                        step_no,
                        snapshot_name,
                        current_node,
                        next_node,
                        policy_version,
                        schema_version,
                        state_json,
                        patch_json,
                        evidence_refs_json,
                        status,
                        parent_snapshot_id,
                        state_hash,
                        error_message,
                    ),
                )
                snapshot_id = int(cursor.lastrowid)
            connection.commit()
            return snapshot_id

    def _connect(self) -> Any:
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            autocommit=False,
        )

    def list_thread_snapshots(self, thread_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE thread_id = %s
            ORDER BY step_no ASC
            """,
            (thread_id,),
        )

    def latest_recoverable_checkpoint(self, thread_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE thread_id = %s
              AND status IN ('SUCCESS', 'HUMAN_APPROVED', 'HUMAN_FEEDBACK', 'HUMAN_MODIFIED')
            ORDER BY step_no DESC
            LIMIT 1
            """,
            (thread_id,),
        )
        return rows[0] if rows else None

    def latest_snapshot_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE run_id = %s
            ORDER BY step_no DESC
            LIMIT 1
            """,
            (run_id,),
        )
        return rows[0] if rows else None

    def latest_snapshot_header_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT
                id,
                run_id,
                business_task,
                thread_id,
                step_no,
                snapshot_name,
                current_node,
                next_node,
                status,
                parent_snapshot_id,
                state_hash,
                error_message,
                created_at,
                updated_at
            FROM agent_state_snapshot
            WHERE run_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_id,),
        )
        return rows[0] if rows else None

    def latest_waiting_human_snapshot(self, run_id: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE run_id = %s
              AND status = 'WAITING_HUMAN'
            ORDER BY step_no DESC
            LIMIT 1
            """,
            (run_id,),
        )
        return rows[0] if rows else None

    def waiting_human_snapshots(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE status = 'WAITING_HUMAN'
            ORDER BY created_at ASC
            """,
            (),
        )

    def child_snapshots(self, parent_snapshot_id: int) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE parent_snapshot_id = %s
            ORDER BY created_at ASC
            """,
            (parent_snapshot_id,),
        )

    def node_snapshots(self, current_node: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT *
            FROM agent_state_snapshot
            WHERE current_node = %s
            ORDER BY created_at DESC
            """,
            (current_node,),
        )

    def _fetch_all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        if pymysql is None:
            raise RuntimeError("Missing dependency: install PyMySQL to read state snapshots from MySQL.")
        with self._connect() as connection:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())


def load_project_env() -> None:
    if load_dotenv is None:
        return
    project_root = Path(__file__).resolve().parents[1]
    for candidate in [project_root / ".env", Path.cwd() / ".env"]:
        if candidate.exists():
            load_dotenv(candidate, override=False)


SNAPSHOT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_state_snapshot (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(64) NOT NULL,
    business_task VARCHAR(128) NOT NULL,
    thread_id VARCHAR(64) NOT NULL,
    step_no INT NOT NULL,
    snapshot_name VARCHAR(128) NOT NULL,
    current_node VARCHAR(128) NOT NULL,
    next_node VARCHAR(128) NULL,
    policy_version VARCHAR(128) NULL,
    schema_version VARCHAR(64) NOT NULL,
    state_json JSON NOT NULL,
    patch_json JSON NOT NULL,
    evidence_refs_json JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    parent_snapshot_id BIGINT NULL,
    state_hash CHAR(64) NOT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    UNIQUE KEY uq_agent_state_snapshot_thread_step (thread_id, step_no),
    KEY idx_run_id (run_id),
    KEY idx_thread_step (thread_id, step_no),
    KEY idx_thread_status_step (thread_id, status, step_no DESC),
    KEY idx_status_created (status, created_at),
    KEY idx_parent_snapshot (parent_snapshot_id),
    KEY idx_current_node_created (current_node, created_at),
    KEY idx_policy_version (policy_version),
    CONSTRAINT fk_agent_state_snapshot_parent
        FOREIGN KEY (parent_snapshot_id)
        REFERENCES agent_state_snapshot(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""
