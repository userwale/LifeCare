"""
app/routers/users.py – User management endpoints.

Rules:
    POST /api/v1/users   → create a new user  (admin only)
    GET  /api/v1/users   → list all users      (admin only)
    GET  /api/v1/users/me → get own profile    (any authenticated user) [placeholder]

Admin guard strategy (simple header-based for now, replace with JWT later):
    Requests must include the header:
        X-Admin-Key: <value of ADMIN_PASSWORD from .env>
    This is a temporary mechanism until a full JWT auth system is built.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, get_current_active_user, get_current_admin_user
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


# ── POST /api/v1/users  ───────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only)",
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> User:
    # ── Check username uniqueness ─────────────────────────────────────────────
    existing = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already taken.",
        )

    # ── Check email uniqueness ────────────────────────────────────────────────
    existing_email = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{payload.email}' is already registered.",
        )

    # ── Create user ───────────────────────────────────────────────────────────
    user = User(
        username=payload.username,
        email=str(payload.email),
        password=hash_password(payload.password),
        role=payload.role,
        is_verified=True,  # Users created by Admin are verified by default
    )
    db.add(user)
    await db.flush()        # get the generated id before commit
    await db.refresh(user)
    return user


# ── GET /api/v1/users  ────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=list[UserRead],
    summary="List all users (admin only)",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.id))
    return list(result.scalars().all())


# ── GET /api/v1/users/me  ─────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserRead,
    summary="Get own profile (any authenticated user)",
)
async def get_own_profile(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Returns the profile of the currently authenticated user."""
    return current_user


# ── GET /api/v1/users/{user_id}  ──────────────────────────────────────────────
@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get user by ID (admin only)",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id={user_id} not found.",
        )
    return user

