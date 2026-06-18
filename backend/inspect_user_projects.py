import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.user import User, UserProject, Project

async def run():
    async with AsyncSessionLocal() as db:
        for user_id in [59, 60]:
            u = await db.get(User, user_id)
            if u:
                print(f"User ID {user_id} ({u.username}):")
                q = select(Project).join(UserProject, UserProject.project_id == Project.id).where(UserProject.user_id == user_id)
                res = await db.execute(q)
                projects = res.scalars().all()
                print(f"  Assigned Projects: {[(p.id, p.code, p.name) for p in projects]}")
            else:
                print(f"User ID {user_id} not found")

asyncio.run(run())
