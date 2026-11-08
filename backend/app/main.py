import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.api import api_router

startup_database_error = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_database_error
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except Exception as exc:
        startup_database_error = type(exc).__name__
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Multi-tenant Project & Employee Progress Tracking System with RBAC, attendance derivation, and burndown analytics.",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


async def database_health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database = "connected"
    except Exception as exc:
        database = "unavailable"
        return {"status": "degraded", "app": settings.APP_NAME, "env": settings.APP_ENV, "database": database, "database_error_type": type(exc).__name__, "startup_database_error": startup_database_error}
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV, "database": database, "startup_database_error": startup_database_error}


@app.get("/health")
async def health():
    return await database_health()


@app.get("/api/health")
async def api_health():
    return await database_health()


@app.get("/api/v1/health/database")
async def api_database_health():
    return await database_health()


# Serve React frontend build when available
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

