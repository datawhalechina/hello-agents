"""Default Uvicorn entry point for local ResumeAgent development."""

import os
from pathlib import Path

from resume_agent.api.app import create_app

DATABASE_PATH = Path(os.environ.get("RESUME_AGENT_DB", "data/resume_agent.db"))
app = create_app(DATABASE_PATH)
