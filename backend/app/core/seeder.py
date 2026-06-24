"""
app/core/seeder.py – Auto-seeds the admin account at application startup.

Logic:
    1. Open an async DB session.
    2. Query the users table for a row where role == admin.
    3. If none found → create the admin using credentials from settings.
    4. If already present → do nothing (idempotent).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.config import settings

logger = logging.getLogger(__name__)


async def seed_admin(session: AsyncSession) -> None:
    """
    Ensure one admin account exists in the database.
    Safe to call on every startup — creates the admin only once.
    """
    # ── Check if any admin already exists ────────────────────────────────────
    result = await session.execute(
        select(User).where(User.role == UserRole.admin).limit(1)
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin is not None:
        if not existing_admin.is_verified:
            existing_admin.is_verified = True
            await session.commit()
            logger.info("✅  Updated existing admin account to be verified.")
        else:
            logger.info("✅  Admin account already exists — skipping seed.")
        return

    # ── Create the admin ──────────────────────────────────────────────────────
    admin = User(
        username=settings.admin_username,
        email=settings.admin_email,
        password=hash_password(settings.admin_password),
        role=UserRole.admin,
        is_verified=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    logger.info(
        "🚀  Admin account created  →  username='%s'  email='%s'",
        admin.username,
        admin.email,
    )
