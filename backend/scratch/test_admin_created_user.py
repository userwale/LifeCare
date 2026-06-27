import asyncio
import httpx
from app.config import settings

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Login as Admin using password flow
        print("1. Logging in as admin...")
        res = await client.post("/api/v1/auth/token", data={
            "username": settings.admin_username,
            "password": settings.admin_password
        })
        print("Admin login status:", res.status_code)
        admin_token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Admin creates a user
        print("\n2. Admin creating a new user...")
        new_username = "admin_created_user"
        new_email = "admin_created@example.com"
        new_password = "Password123"
        res = await client.post("/api/v1/users/", headers=headers, json={
            "username": new_username,
            "email": new_email,
            "password": new_password,
            "role": "user"
        })
        print("Create user status:", res.status_code)
        user_data = res.json()
        print("Created user data:", user_data)

        # 3. User tries to log in
        print("\n3. User logging in...")
        res = await client.post("/api/v1/auth/login", json={
            "username_or_email": new_username,
            "password": new_password
        })
        print("Login status:", res.status_code)
        login_res = res.json()
        print("Login response:", login_res)

        if res.status_code == 200 and login_res.get("status") == "otp_sent":
            # 4. Fetch the OTP code from the DB for this user
            import sqlite3
            conn = sqlite3.connect("lifecare.db")
            cursor = conn.cursor()
            cursor.execute("SELECT code, purpose FROM otp_codes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_data["id"],))
            otp_code, purpose = cursor.fetchone()
            print(f"\n4. Retrieved OTP from DB: code={otp_code}, purpose={purpose}")

            # 5. Verify the login OTP
            print("\n5. Verifying login OTP...")
            res = await client.post("/api/v1/auth/verify-login", json={
                "email": new_email,
                "code": otp_code
            })
            print("Verify login status:", res.status_code)
            print("Verify login response:", res.json())
            
            # Clean up the user
            cursor.execute("DELETE FROM otp_codes WHERE user_id = ?", (user_data["id"],))
            cursor.execute("DELETE FROM users WHERE id = ?", (user_data["id"],))
            conn.commit()
            conn.close()

if __name__ == "__main__":
    asyncio.run(main())
