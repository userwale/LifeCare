"""
app/models/posture.py – SQLAlchemy ORM model for the posture_records table.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PostureRecord(Base):
    __tablename__ = "posture_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    posture_image: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    posture_status: Mapped[str] = mapped_column(
        String(10),  # "GOOD" | "BAD"
        nullable=False,
    )

    disease_risk: Mapped[str] = mapped_column(
        String(50),  # "Cervicalgie" | "Lombalgie" | "Radiculopathie" | "None"
        nullable=False,
        default="None",
        server_default="None",
    )

    disease_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="posture_records")

    def __repr__(self) -> str:
        return (
            f"<PostureRecord id={self.id} user_id={self.user_id} status={self.posture_status!r} "
            f"risk={self.disease_risk!r} prob={self.disease_probability:.2f}%>"
        )
