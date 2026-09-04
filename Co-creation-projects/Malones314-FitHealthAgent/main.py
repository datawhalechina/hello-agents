from dotenv import load_dotenv

load_dotenv()

import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse

from fithealth_agent.routes.chat import router as chat_router
from fithealth_agent.routes.health import (
    audit_router as health_audit_router,
    daily_router as health_daily_router,
    router as health_router,
    storage_router as health_storage_router,
)
from fithealth_agent.routes.logout import router as logout_router
from fithealth_agent.routes.maintenance_ops import (
    backup_router,
    router as maintenance_router,
)
from fithealth_agent.routes.memories import router as memories_router
from fithealth_agent.routes.plans import router as plans_router
from fithealth_agent.routes.records import (
    checkins_router,
    delete_router as record_delete_router,
    router as records_router,
)
from fithealth_agent.routes.settings import (
    reset_router as profile_reset_router,
    router as settings_router,
)
from fithealth_agent.routes.uploads import (
    activity_router as upload_activity_router,
    food_router,
    router as uploads_router,
)
from fithealth_agent.routes.workout_state import (
    pending_router as pending_workout_router,
    router as workout_state_router,
)
from fithealth_agent.runtime.middleware import register as register_middleware


for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


app = FastAPI(title="FitHealthAgent")
register_middleware(app)


def _include_router(router: APIRouter) -> None:
    """Include a no-prefix router while preserving the frozen flat route order."""
    app.include_router(router)
    # FastAPI 0.141 stores includes as lazy nodes. These routers use no include
    # options, so replacing the node with its routes preserves the old contract.
    app.router.routes[-1:] = router.routes


_include_router(food_router)

TEMPLATES_DIR = Path(__file__).with_name("templates")


@lru_cache(maxsize=1)
def load_index_html() -> str:
    return (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return load_index_html()


_include_router(chat_router)
_include_router(logout_router)
_include_router(uploads_router)
_include_router(workout_state_router)
_include_router(records_router)
_include_router(health_storage_router)
_include_router(checkins_router)
_include_router(backup_router)
_include_router(health_audit_router)
_include_router(plans_router)
_include_router(record_delete_router)
_include_router(memories_router)
_include_router(health_daily_router)
_include_router(settings_router)
_include_router(upload_activity_router)
_include_router(health_router)
_include_router(pending_workout_router)
_include_router(profile_reset_router)
_include_router(maintenance_router)


# Compatibility exports for tests and older local callers. Only stable helpers
# that are not replaceable runtime dependencies live here. Remove an alias after
# its callers import the owning module directly; never add deps-backed stores,
# agents, routers, or model functions because that would create silent dead stubs.
from fithealth_agent import workout_store
from fithealth_agent.domain.intent_rules import navigation_only_message
from fithealth_agent.domain.memory_view import temporary_constraint_for_message
from fithealth_agent.domain.plan_context import format_plan_context
from fithealth_agent.domain.plan_validation import (
    constraint_regions,
    plan_validation_fact_usage,
    validate_generated_training_plan,
)
from fithealth_agent.domain.recovery_view import (
    _format_muscle_recovery_lines,
    _recovery_checkin_items,
    _recovery_context_payload,
    _subject_recovery_regions,
    explicitly_requested_recovery_regions,
    parse_garmin_recovery_hours,
)
from fithealth_agent.health_importer import HealthImportError
from fithealth_agent.health_safety import screen_health_risk
from fithealth_agent.maintenance import MAINTENANCE
from fithealth_agent.runtime.deps import _sign_analysis_confidence


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9999)
