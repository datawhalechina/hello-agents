from fastapi import APIRouter
from app.api.v1.endpoints import users, personas, forums, agents, auth, god, moderators

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(personas.router, prefix="/personas", tags=["personas"])
api_router.include_router(forums.router, prefix="/forums", tags=["forums"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(god.router, prefix="/god", tags=["god"])
api_router.include_router(moderators.router, prefix="/moderators", tags=["moderators"])
