import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import Project, Role
from app.models.settings_master import Position, Employee

async def main():
    async with AsyncSessionLocal() as db:
        lines = []
        
        # Projects
        res = await db.execute(select(Project))
        projects = res.scalars().all()
        lines.append("--- PROJECTS ---")
        for p in projects:
            lines.append(f"ID: {p.id}, Code: {p.code}, Name: {p.name}")
            
        # Roles
        res = await db.execute(select(Role))
        roles = res.scalars().all()
        lines.append("\n--- ROLES ---")
        for r in roles:
            lines.append(f"ID: {r.id}, Code: {r.code}, Name: {r.name}")
            
        # Positions
        res = await db.execute(select(Position))
        positions = res.scalars().all()
        lines.append("\n--- POSITIONS ---")
        for pos in positions:
            lines.append(f"ID: {pos.id}, Name: {pos.name}, Code: {pos.code}, RoleID: {pos.role_id}, ProjectID: {pos.project_id}, ParentPositionID: {pos.parent_position_id}")
            
        with open("scripts/db_inspect.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("Wrote output to scripts/db_inspect.txt")

if __name__ == "__main__":
    asyncio.run(main())
