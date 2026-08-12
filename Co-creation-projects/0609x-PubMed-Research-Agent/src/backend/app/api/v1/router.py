# -*- coding: utf-8 -*-
"""Aggregate v1 API routes."""
from __future__ import annotations

from fastapi import APIRouter
from backend.app.api.v1 import graph, health, rag, search, translate


router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(search.router)
router.include_router(rag.router)
router.include_router(graph.router)
router.include_router(translate.router)
