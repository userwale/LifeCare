"""
app/routers/auth.py – Authentication and OTP verification endpoints.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.email import send_otp_email
from app.core.security import hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.user import User, UserRole
from app.models.otp import OTPCode, OTPPurpose
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import (
    LoginRequest,
    OTPVerify,
    OTPResend,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Helper to generate and send OTP ───────────────────────────────────────────
async def create_and_send_otp(
    db: AsyncSession,
    user: User,
    purpose: OTPPurpose,
) -> str:
    """
    Generates a new 6-digit OTP code, marks older OTPs as used,
    saves the code to the DB, and triggers email sending.
    """
    # 1. Mark previous active OTPs for this user & purpose as used
    await db.execute(
        update(OTPCode)
        .where(OTPCode.user_id == user.id)
        .where(OTPCode.purpose == purpose)
        .where(OTPCode.is_used == False)
        .values(is_used=True)
    )

    # 2. Generate a secure 6-digit numeric OTP code
    otp_code = "".join(secrets.choice("0123456789") for _ in range(6))

    # 3. Save new OTP to the database
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)
    db_otp = OTPCode(
        user_id=user.id,
        code=otp_code,
        purpose=purpose,
        expires_at=expires_at,
    )
    db.add(db_otp)
    await db.flush()

    # 4. Trigger email sending
    await send_otp_email(user.email, otp_code, purpose.value)
    return otp_code


# ── POST /register ───────────────────────────────────────────────────────────
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (requires OTP email verification)",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Check unique username
    existing_username = await db.execute(
        select(User).where(User.username == payload.username)
    )
    if existing_username.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already taken.",
        )

    # 2. Check unique email
    existing_email = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{payload.email}' is already registered.",
        )

    # 3. Create user (inactive/unverified by default)
    user = User(
        username=payload.username,
        email=str(payload.email),
        password=hash_password(payload.password),
        role=UserRole.user,  # default signup is always user
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # 4. Send Registration OTP
    await create_and_send_otp(db, user, OTPPurpose.registration)

    return {
        "message": "Registration successful. Please verify your email with the OTP code sent to you.",
        "email": user.email,
    }


# ── POST /verify-registration ────────────────────────────────────────────────
@router.post(
    "/verify-registration",
    response_model=Token,
    summary="Verify registration OTP and activate user account",
)
async def verify_registration(
    payload: OTPVerify,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Retrieve user
    user_result = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # 2. Check if already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already verified.",
        )

    # 3. Query active registration OTP
    otp_result = await db.execute(
        select(OTPCode)
        .where(OTPCode.user_id == user.id)
        .where(OTPCode.code == payload.code)
        .where(OTPCode.purpose == OTPPurpose.registration)
        .where(OTPCode.is_used == False)
        .order_by(OTPCode.id.desc())
        .limit(1)
    )
    otp_record = otp_result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    # 4. Check expiration
    now_utc = datetime.now(timezone.utc)
    expires_at_utc = otp_record.expires_at.replace(tzinfo=timezone.utc)
    if expires_at_utc < now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired.",
        )

    # 5. Activate user and mark OTP as used
    user.is_verified = True
    otp_record.is_used = True
    await db.flush()

    # 6. Generate access token
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


# ── POST /login ──────────────────────────────────────────────────────────────
@router.post(
    "/login",
    summary="Verify password and send a login OTP (2FA)",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Find user by username or email
    user_result = await db.execute(
        select(User).where(
            (User.username == payload.username_or_email) |
            (User.email == payload.username_or_email)
        )
    )
    user = user_result.scalar_one_or_none()

    # 2. Check credentials
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    # 3. Check if verified
    if not user.is_verified:
        # Resend registration OTP automatically
        await create_and_send_otp(db, user, OTPPurpose.registration)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email is not verified. A verification code has been sent to your email.",
        )

    # 4. Generate and send Login OTP
    await create_and_send_otp(db, user, OTPPurpose.login)

    return {
        "status": "otp_sent",
        "email": user.email,
        "message": "A verification code has been sent to your email.",
    }


# ── POST /verify-login ───────────────────────────────────────────────────────
@router.post(
    "/verify-login",
    response_model=Token,
    summary="Verify login OTP (2FA) and return access token",
)
async def verify_login(
    payload: OTPVerify,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Retrieve user
    user_result = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not verified.",
        )

    # 2. Query active login OTP
    otp_result = await db.execute(
        select(OTPCode)
        .where(OTPCode.user_id == user.id)
        .where(OTPCode.code == payload.code)
        .where(OTPCode.purpose == OTPPurpose.login)
        .where(OTPCode.is_used == False)
        .order_by(OTPCode.id.desc())
        .limit(1)
    )
    otp_record = otp_result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    # 3. Check expiration
    now_utc = datetime.now(timezone.utc)
    expires_at_utc = otp_record.expires_at.replace(tzinfo=timezone.utc)
    if expires_at_utc < now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired.",
        )

    # 4. Mark OTP as used
    otp_record.is_used = True
    await db.flush()

    # 5. Generate access token
    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


# ── POST /token (OAuth2 Password Grant bypass) ──────────────────────────────
@router.post(
    "/token",
    summary="Standard OAuth2 compatible login (bypasses OTP, for dev/Swagger docs)",
)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Find user by username or email
    user_result = await db.execute(
        select(User).where(
            (User.username == form_data.username) |
            (User.email == form_data.username)
        )
    )
    user = user_result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email is not verified.",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ── POST /resend-otp ──────────────────────────────────────────────────────────
@router.post(
    "/resend-otp",
    summary="Resend a new OTP verification code",
)
async def resend_otp(
    payload: OTPResend,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Retrieve user
    user_result = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # 2. Check if verified (for registration purpose)
    if payload.purpose == OTPPurpose.registration and user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already verified.",
        )

    # 3. Create and send new OTP
    await create_and_send_otp(db, user, payload.purpose)

    return {
        "message": f"A new verification code has been sent to {user.email}.",
    }


# ── POST /forgot-password ─────────────────────────────────────────────────────
@router.post(
    "/forgot-password",
    summary="Request a password reset OTP code",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Find user
    user_result = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    user = user_result.scalar_one_or_none()

    # 2. If user exists, create and send OTP
    if user:
        await create_and_send_otp(db, user, OTPPurpose.password_reset)

    # Return success regardless to prevent user enumeration
    return {
        "message": "If the email is registered in our system, a password reset code has been sent.",
    }


# ── POST /reset-password ──────────────────────────────────────────────────────
@router.post(
    "/reset-password",
    summary="Reset password using OTP code",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # 1. Find user
    user_result = await db.execute(
        select(User).where(User.email == str(payload.email))
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or verification code.",
        )

    # 2. Query active password reset OTP
    otp_result = await db.execute(
        select(OTPCode)
        .where(OTPCode.user_id == user.id)
        .where(OTPCode.code == payload.code)
        .where(OTPCode.purpose == OTPPurpose.password_reset)
        .where(OTPCode.is_used == False)
        .order_by(OTPCode.id.desc())
        .limit(1)
    )
    otp_record = otp_result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or verification code.",
        )

    # 3. Check expiration
    now_utc = datetime.now(timezone.utc)
    expires_at_utc = otp_record.expires_at.replace(tzinfo=timezone.utc)
    if expires_at_utc < now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired.",
        )

    # 4. Reset password and mark OTP as used
    user.password = hash_password(payload.new_password)
    otp_record.is_used = True
    await db.flush()

    return {
        "message": "Password reset successful. You can now log in with your new password.",
    }


# ── POST /test-email  (dev only) ──────────────────────────────────────────────
@router.post(
    "/test-email",
    summary="[DEV] Send a test OTP email to verify SMTP configuration",
    include_in_schema=settings.debug,   # hidden in production
)
async def test_email(email: str) -> dict:
    """
    Sends a dummy OTP code to the given email address.
    Use this to verify your SMTP credentials before testing the full auth flow.
    Only available when DEBUG=true.
    """
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    await send_otp_email(email=email, code="123456", purpose="login")
    return {
        "message": f"Test email dispatched to {email}. Check your inbox (or backend console if SMTP is not configured).",
        "smtp_configured": bool(settings.smtp_username and settings.smtp_password),
    }

