import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.master import Position, Employee

async def inspect():
    async with AsyncSessionLocal() as db:
        # Search specifically for DEO positions in the screenshot
        q = select(Position).where(Position.code.like("DEO-%")).limit(10)
        res = await db.execute(q)
        positions = res.scalars().all()
        print(f"Found {len(positions)} DEO positions:")
        for p in positions:
            print(f"\nPosition: ID={p.id}, Code={p.code}, Name={p.name}, employee_id={p.employee_id}")
            
            # Find employees pointing to this position via Employee.position_id
            q_emp = select(Employee).where(Employee.position_id == p.id)
            res_emp = await db.execute(q_emp)
            emps = res_emp.scalars().all()
            print(f"  Employees with position_id == {p.id}: {[(e.id, e.employee_code, e.name) for e in emps]}")

            # Find employee pointing to this position via Position.employee_id
            if p.employee_id:
                emp_direct = await db.get(Employee, p.employee_id)
                print(f"  Direct employee (employee_id): {(emp_direct.id, emp_direct.employee_code, emp_direct.name) if emp_direct else 'None'}")
            else:
                print("  Direct employee (employee_id): None")

asyncio.run(inspect())
