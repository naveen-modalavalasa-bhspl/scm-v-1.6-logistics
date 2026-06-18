import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from app.models.settings_master import Position

async def run():
    async with AsyncSessionLocal() as db:
        p = await db.get(Position, 169)
        if p:
            print(f"Position 169: ID={p.id}, Code={p.code}, Name={p.name}, ProjectID={p.project_id}, RoleID={p.role_id}")
        else:
            print("Position 169 not found!")

asyncio.run(run())
