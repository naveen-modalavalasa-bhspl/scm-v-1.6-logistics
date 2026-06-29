from fastapi.testclient import TestClient
from app.main import app
from app.database import AsyncSessionLocal
from app.models.user import User
from app.api.v1.auth import create_access_token
from sqlalchemy import select
import asyncio

async def get_token():
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).where(User.is_active == True).limit(1))
        user = user_res.scalar_one_or_none()
        return create_access_token(data={"sub": str(user.id), "username": user.username})

token = asyncio.run(get_token())
client = TestClient(app)
print("Sending request via TestClient...")
try:
    res = client.post(
        "/api/v1/users/employees/sync-api",
        headers={"Authorization": f"Bearer {token}"}
    )
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    import traceback
    traceback.print_exc()
