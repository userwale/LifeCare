"""
app/models/otp.py – SQLAlchemy ORM model for OTP verification codes.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OTPPurpose(str, enum.Enum):
    registration = "registration"
    login = "login"
    password_reset = "password_reset"


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    purpose: Mapped[OTPPurpose] = mapped_column(
        Enum(OTPPurpose, name="otppurpose"),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # Relationships
    user = relationship("User", back_populates="otp_codes")

    def __repr__(self) -> str:
        return f"<OTPCode id={self.id} user_id={self.user_id} purpose={self.purpose} is_used={self.is_used}>"
