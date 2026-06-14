import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.api.v1.users import list_users

async def main():
    async with AsyncSessionLocal() as db:
        for username in ["mahendra.y", "george"]:
            res = await db.execute(select(User).where(User.username == username))
            user = res.scalar_one_or_none()
            if not user:
                print(f"User {username} not found")
                continue
            
            print(f"\nTesting settings API for user: {username} (ID: {user.id})")
            try:
                # Call list_users directly simulating the endpoint call
                response = await list_users(
                    page=1,
                    page_size=20,
                    search=None,
                    is_active=None,
                    status=None,
                    user_type=None,
                    department=None,
                    role_id=None,
                    db=db,
                    current_user=user
                )
                print(f"SUCCESS: Returned {len(response.get('items', []))} users (total: {response.get('total')})")
            except Exception as e:
                print(f"FAILED with error: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
