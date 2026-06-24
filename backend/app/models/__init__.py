# app/models/__init__.py
# Import ALL ORM models here so Alembic can auto-detect them.

from app.models.user import User, UserRole  # noqa: F401
from app.models.otp import OTPCode, OTPPurpose  # noqa: F401

