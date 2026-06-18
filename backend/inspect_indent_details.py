import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.indent import Indent
from app.models.user import Project

async def run():
    async with AsyncSessionLocal() as db:
        for ind_id in [82, 81, 71, 70, 69]:
            ind = await db.get(Indent, ind_id)
            if ind:
                proj = await db.get(Project, ind.project_id) if ind.project_id else None
                print(f"Indent ID {ind_id}: Number={ind.indent_number}, Status={ind.status}, ProjectID={ind.project_id}, ProjectName={proj.name if proj else 'None'}")
            else:
                print(f"Indent ID {ind_id} not found")

asyncio.run(run())
