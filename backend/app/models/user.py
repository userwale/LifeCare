"""
app/models/user.py – SQLAlchemy ORM model for the User table.

Columns:
    id          : Primary key (auto-increment)
    username    : Unique login name
    password    : Bcrypt-hashed password (never store plain text)
    role        : "user" | "admin"  – default "user"
    email       : Unique email address
    created_at  : UTC timestamp set automatically on creation
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Role enum ─────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    user  = "user"
    admin = "admin"


# ── ORM Model ─────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password: Mapped[str] = mapped_column(
        String(255),          # bcrypt hash ≈ 60 chars, give room
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.user,
        server_default=UserRole.user.value,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    otp_codes: Mapped[list[OTPCode]] = relationship(
        "OTPCode",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    posture_records: Mapped[list[PostureRecord]] = relationship(
        "PostureRecord",
        back_populates="user",
        cascade="all, delete-orphan",
    )


    # ── helpers ───────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role} is_verified={self.is_verified}>"

