import asyncio
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole, Role
from app.api.v1.auth import create_access_token

async def main():
    async with AsyncSessionLocal() as db:
        # Find a user with super_admin role
        stmt = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == "super_admin")
            .limit(1)
        )
        user_res = await db.execute(stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            print("No super_admin user found!")
            return
            
        print(f"Found super_admin user: {user.username}")
        token = create_access_token(data={"sub": user.username})
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Post to sync-api with no body
        res = await client.post("http://localhost:8000/api/v1/users/employees/sync-api", headers=headers)
        print("Status:", res.status_code)
        print("Response:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
