from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.diet import router as diet_router
from api.routes.health import router as health_router
from memory.store import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="HealthRecordAgent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api")
app.include_router(diet_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许全部
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)