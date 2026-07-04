"""
tests/test_auth.py – Integration tests for backend auth and OTP module.
"""
from __future__ import annotations

import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.otp import OTPCode, OTPPurpose
from app.config import settings


@pytest.fixture(autouse=True, scope="module")
async def setup_database():
    from app.core.seeder import seed_admin
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await seed_admin(session)


@pytest.mark.asyncio
async def test_complete_auth_flow():
    # Generate unique test user credentials
    uid = uuid.uuid4().hex[:6]
    username = f"user_{uid}"
    email = f"user_{uid}@example.com"
    password = f"Pass1234_{uid}"

    # Use HTTPX client to query endpoints
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        # ── 1. Register a new user ──
        reg_payload = {
            "username": username,
            "email": email,
            "password": password,
            "role": "user"
        }
        response = await client.post("/api/v1/auth/register", json=reg_payload)
        assert response.status_code == 201
        data = response.json()
        assert "Registration successful" in data["message"]
        assert data["email"] == email

        # ── 2. Verify User exists in database and is_verified is False ──
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.username == username))
            user = res.scalar_one_or_none()
            assert user is not None
            assert user.is_verified is False

            # Retrieve the registration OTP code from DB
            otp_res = await session.execute(
                select(OTPCode)
                .where(OTPCode.user_id == user.id)
                .where(OTPCode.purpose == OTPPurpose.registration)
                .where(OTPCode.is_used == False)
            )
            otp_record = otp_res.scalar_one_or_none()
            assert otp_record is not None
            reg_otp_code = otp_record.code

        # ── 3. Verify registration with invalid OTP ──
        verify_payload = {
            "email": email,
            "code": "000000"  # wrong code
        }
        response = await client.post("/api/v1/auth/verify-registration", json=verify_payload)
        assert response.status_code == 400
        assert "Invalid verification code" in response.json()["detail"]

        # ── 4. Verify registration with correct OTP ──
        verify_payload["code"] = reg_otp_code
        response = await client.post("/api/v1/auth/verify-registration", json=verify_payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == username
        user_token = data["access_token"]

        # ── 5. Verify User is_verified is now True ──
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.username == username))
            user = res.scalar_one_or_none()
            assert user.is_verified is True

        # ── 6. Try to login with incorrect credentials ──
        login_payload = {
            "username_or_email": username,
            "password": "WrongPassword123"
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 401

        # ── 7. Login with correct credentials (should login directly since role is user) ──
        login_payload["password"] = password
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        login_token = data["access_token"]

        # ── 9. Access protected profile route ──
        headers = {"Authorization": f"Bearer {login_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == username

        # ── 10. Access profile without token -> 401 ──
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

        # ── 11. Request forgot password reset OTP ──
        response = await client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert response.status_code == 200

        # Retrieve password reset OTP code from DB
        async with AsyncSessionLocal() as session:
            otp_res = await session.execute(
                select(OTPCode)
                .where(OTPCode.user_id == user.id)
                .where(OTPCode.purpose == OTPPurpose.password_reset)
                .where(OTPCode.is_used == False)
            )
            otp_record = otp_res.scalar_one_or_none()
            assert otp_record is not None
            reset_otp_code = otp_record.code

        # ── 12. Reset password ──
        new_password = f"NewPass123_{uid}"
        reset_payload = {
            "email": email,
            "code": reset_otp_code,
            "new_password": new_password
        }
        response = await client.post("/api/v1/auth/reset-password", json=reset_payload)
        assert response.status_code == 200
        assert "Password reset successful" in response.json()["message"]

        # ── 13. Login with new password (should login directly since role is user) ──
        login_payload["password"] = new_password
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_admin_bypass_and_authorization():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        # ── 1. Login seeded Admin using OAuth2 password flow (direct JWT return) ──
        token_payload = {
            "username": settings.admin_username,
            "password": settings.admin_password
        }
        response = await client.post("/api/v1/auth/token", data=token_payload)
        assert response.status_code == 200
        admin_token = response.json()["access_token"]

        # ── 2. Admin fetches all users -> 200 OK ──
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200
        users_list = response.json()
        assert len(users_list) >= 1

        # ── 3. Try to access user list with normal user token -> 403 Forbidden ──
        # Create a quick verified user for this test
        uid = uuid.uuid4().hex[:6]
        username = f"norm_{uid}"
        email = f"norm_{uid}@example.com"
        password = f"Pass1234_{uid}"

        # Register and verify
        await client.post("/api/v1/auth/register", json={
            "username": username, "email": email, "password": password
        })
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(User).where(User.username == username))
            norm_user = res.scalar_one()
            otp_res = await session.execute(
                select(OTPCode).where(OTPCode.user_id == norm_user.id).where(OTPCode.purpose == OTPPurpose.registration)
            )
            norm_otp = otp_res.scalars().first().code

        verify_res = await client.post("/api/v1/auth/verify-registration", json={
            "email": email, "code": norm_otp
        })
        norm_token = verify_res.json()["access_token"]

        # Fetch all users with norm user token -> 403
        norm_headers = {"Authorization": f"Bearer {norm_token}"}
        response = await client.get("/api/v1/users/", headers=norm_headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_login_otp_flow():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # ── 1. Login admin via normal login flow (should prompt OTP/2FA) ──
        login_payload = {
            "username_or_email": settings.admin_email,
            "password": settings.admin_password
        }
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "otp_sent"
        assert data["email"] == settings.admin_email

        # Retrieve login OTP code from DB
        async with AsyncSessionLocal() as session:
            admin_res = await session.execute(select(User).where(User.email == settings.admin_email))
            admin_user = admin_res.scalar_one()
            otp_res = await session.execute(
                select(OTPCode)
                .where(OTPCode.user_id == admin_user.id)
                .where(OTPCode.purpose == OTPPurpose.login)
                .where(OTPCode.is_used == False)
            )
            otp_record = otp_res.scalars().first()
            assert otp_record is not None
            admin_otp = otp_record.code

        # ── 2. Verify admin login with correct OTP ──
        response = await client.post("/api/v1/auth/verify-login", json={
            "email": settings.admin_email,
            "code": admin_otp
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"

