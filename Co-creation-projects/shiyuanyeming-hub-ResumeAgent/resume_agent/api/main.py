"""Default Uvicorn entry point for local ResumeAgent development."""

import os
from pathlib import Path
from typing import Mapping, Optional

from resume_agent.agents.runtime import build_mentor_runtime
from resume_agent.api.app import create_app


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(dotenv_path=Path(".env"), override=False)


def create_default_app(environ: Optional[Mapping[str, str]] = None):
    global DATABASE_PATH
    if environ is None:
        _load_dotenv()
        values: Mapping[str, str] = os.environ
    else:
        values = environ
    runtime = build_mentor_runtime(values)
    database_path = Path(values.get("RESUME_AGENT_DB", "data/resume_agent.db"))
    DATABASE_PATH = database_path
    return create_app(
        database_path,
        fact_audit_agent=runtime.fact_auditor,
        question_writer=runtime.question_writer,
        agent_capabilities=runtime.capabilities,
    )


app = create_default_app()
