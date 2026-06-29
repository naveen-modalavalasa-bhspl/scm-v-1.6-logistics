import asyncio
import httpx
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.api.v1.auth import create_access_token

async def main():
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).where(User.is_active == True).limit(1))
        user = user_res.scalar_one_or_none()
        token = create_access_token(data={"sub": user.username})
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. Post to sync-api with no body
        res = await client.post("http://localhost:8000/api/v1/users/employees/sync-api", headers=headers)
        print("1. Status:", res.status_code)
        print("1. Response:", res.text)
        
        # 2. Post to sync-api with json=None
        res = await client.post("http://localhost:8000/api/v1/users/employees/sync-api", json=None, headers=headers)
        print("2. Status:", res.status_code)
        print("2. Response:", res.text)
        
        # 3. Post to sync-api with json={}
        res = await client.post("http://localhost:8000/api/v1/users/employees/sync-api", json={}, headers=headers)
        print("3. Status:", res.status_code)
        print("3. Response:", res.text)

if __name__ == "__main__":
    asyncio.run(main())
