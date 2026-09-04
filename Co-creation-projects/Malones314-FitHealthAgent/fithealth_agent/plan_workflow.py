"""Small deterministic workflow state machine for plan generation."""
from __future__ import annotations

from enum import StrEnum


class PlanWorkflowState(StrEnum):
    IDLE = "idle"
    NEEDS_CLARIFICATION = "needs_clarification"
    CONSTRAINT_CONFLICT = "constraint_conflict"
    READY_TO_GENERATE = "ready_to_generate"
    COMPLETED = "completed"
    AWAITING_SAVE = "awaiting_save"
    VALIDATION_FAILED = "validation_failed"
    SAVED = "saved"


def state_for_context(context: dict[str, object]) -> PlanWorkflowState:
    if context.get("blocking_reasons"):
        return PlanWorkflowState.CONSTRAINT_CONFLICT
    if context.get("clarification_required"):
        return PlanWorkflowState.NEEDS_CLARIFICATION
    return PlanWorkflowState.READY_TO_GENERATE


def state_after_generation(*, artifact: object, validation_failed: bool) -> PlanWorkflowState:
    if validation_failed:
        return PlanWorkflowState.VALIDATION_FAILED
    if artifact:
        return PlanWorkflowState.AWAITING_SAVE
    return PlanWorkflowState.COMPLETED
