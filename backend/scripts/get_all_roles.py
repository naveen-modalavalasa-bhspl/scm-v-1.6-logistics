import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import Role

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Role))
        roles = res.scalars().all()
        for r in roles:
            print(f"ID: {r.id}, Code: {r.code}, Name: {r.name}")

if __name__ == "__main__":
    asyncio.run(main())
