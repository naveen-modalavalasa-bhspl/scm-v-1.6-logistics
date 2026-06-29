import asyncio
from app.database import AsyncSessionLocal
from app.api.v1.users import sync_employees_from_external_api
from app.models.user import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).limit(1))
        user = user_res.scalar_one_or_none()
        print(f"Calling endpoint with user: {user.username if user else 'None'}")
        try:
            res = await sync_employees_from_external_api(db=db, current_user=user)
            print("Success:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
