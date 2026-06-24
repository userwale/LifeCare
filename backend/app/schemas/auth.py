"""
app/schemas/auth.py – Pydantic schemas for authentication and OTP verification.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.otp import OTPPurpose
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., examples=["john_doe", "john@example.com"])
    password: str = Field(..., examples=["Str0ngP@ss!"])


class OTPVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, examples=["123456"])


class OTPResend(BaseModel):
    email: EmailStr
    purpose: OTPPurpose


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, examples=["123456"])
    new_password: str = Field(..., min_length=8, examples=["NewStr0ngP@ss!"])

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
