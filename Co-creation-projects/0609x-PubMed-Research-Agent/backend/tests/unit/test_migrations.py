from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _config(database_path: Path) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "backend" / "alembic"))
    config.set_main_option(
        "sqlalchemy.url", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    return config


def test_migrations_preserve_legacy_data_and_add_job_fields(tmp_path):
    database_path = tmp_path / "migration.db"
    config = _config(database_path)

    command.upgrade(config, "0001_initial")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO searches (
                query_text, pubmed_query, max_results, total_found,
                status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("legacy query", "legacy query", 20, 1, "completed", ""),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(searches)")
        }
        row = connection.execute(
            """
            SELECT query_text, language, search_mode, sort_by,
                   min_year, max_year, min_impact_factor,
                   job_id, cancel_requested, updated_at,
                   started_at, completed_at,
                   progress_percent, progress_stage, progress_message
            FROM searches
            """
        ).fetchone()

    assert {
        "language",
        "search_mode",
        "sort_by",
        "min_year",
        "max_year",
        "min_impact_factor",
        "job_id",
        "cancel_requested",
        "updated_at",
        "started_at",
        "completed_at",
        "progress_percent",
        "progress_stage",
        "progress_message",
    }.issubset(columns)
    assert row[:7] == (
        "legacy query",
        "en",
        "advanced",
        "relevance",
        None,
        None,
        None,
    )
    assert row[7] is None
    assert row[8] == 0
    assert row[9] is not None
    assert row[10:12] == (None, None)
    assert row[12:] == (100, "completed", "")
