import asyncio
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.api.v1.auth import create_access_token

async def main():
    async with AsyncSessionLocal() as db:
        # Get an admin user
        user_res = await db.execute(
            select(User).where(User.is_active == True).limit(10)
        )
        users = user_res.scalars().all()
        admin_user = None
        for u in users:
            # Let's find one with admin permissions
            admin_user = u
            break

        if not admin_user:
            print("No active user found.")
            return

        # Generate a valid token
        token = create_access_token(data={"sub": admin_user.username})
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # Try POSTing with null body (like axios does)
            res = await client.post(
                "http://localhost:8000/api/v1/users/employees/sync-api",
                json=None,
                headers=headers
            )
            print("POST with json=None status:", res.status_code)
            print("Response:", res.text)

            # Try POSTing with empty string/no body
            res2 = await client.post(
                "http://localhost:8000/api/v1/users/employees/sync-api",
                content=b"",
                headers=headers
            )
            print("POST with empty body status:", res2.status_code)
            print("Response:", res2.text)

if __name__ == "__main__":
    asyncio.run(main())
