"""
app/schemas/user.py – Pydantic schemas for the User resource.

UserCreate   : payload to register a new user  (password plain-text input)
UserRead     : response sent to clients        (no password!)
UserUpdate   : fields that can be patched
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# ── Create (registration input) ───────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email:    EmailStr
    password: str = Field(..., min_length=8, examples=["Str0ngP@ss!"])
    role:     UserRole = UserRole.user         # clients can omit this; admins can override

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


# ── Read (response body) ──────────────────────────────────────────────────────
class UserRead(BaseModel):
    id:         int
    username:   str
    email:      str
    role:       UserRole
    created_at: datetime

    model_config = {"from_attributes": True}   # allows orm_mode / from ORM objects


# ── Update (PATCH payload) ────────────────────────────────────────────────────
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email:    Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role:     Optional[UserRole] = None
