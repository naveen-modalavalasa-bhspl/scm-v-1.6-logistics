import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.user import Role

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Role))
        roles = res.scalars().all()
        for r in roles:
            print(f"Role ID: {r.id}, Code: {r.code}, Name: {r.name}")

asyncio.run(run())
