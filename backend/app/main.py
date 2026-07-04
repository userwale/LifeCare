"""
app/main.py – FastAPI application entry point.

Startup sequence:
    1. Create all DB tables (dev convenience — use Alembic in prod).
    2. Seed the admin account if it doesn't exist yet.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, AsyncSessionLocal, engine
import os
from fastapi.staticfiles import StaticFiles
from app.core.seeder import seed_admin
from app.routers import users_router, auth_router, ai_router, chatbot_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅  Database tables ready.")

    # 2. Seed admin account
    async with AsyncSessionLocal() as session:
        await seed_admin(session)

    yield

    # Cleanup on shutdown
    await engine.dispose()
    logger.info("🛑  Database engine disposed.")


# ── Application factory ────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static File Hosting ────────────────────────────────────────────────────────
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ai_router)
app.include_router(chatbot_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Returns 200 if the API is running."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
