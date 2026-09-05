"""Shared response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    app_version: str
