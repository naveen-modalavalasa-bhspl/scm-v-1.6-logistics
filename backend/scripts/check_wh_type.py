import asyncio
import sys
sys.path.insert(0, '.')
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.warehouse import Warehouse

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Warehouse))
        whs = res.scalars().all()
        for wh in whs:
            print(f"ID: {wh.id:<3} | Name: {wh.name:<40} | Type: {wh.type} | Active: {wh.is_active}")

if __name__ == "__main__":
    asyncio.run(main())
