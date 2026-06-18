import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.settings_master import Position, Employee
from app.models.user import User

async def run_inspection():
    async with AsyncSessionLocal() as db:
        for pos_id in [169, 3049, 2178, 2131]:
            p = await db.get(Position, pos_id)
            if p:
                print(f"=== POSITION {pos_id} ===")
                print(f"  Name: {p.name}")
                print(f"  Code: {p.code}")
                print(f"  Role ID: {p.role_id}")
                print(f"  Project ID: {p.project_id}")
                print(f"  Parent Position ID: {p.parent_position_id}")
                print(f"  Employee ID (Position.employee_id): {p.employee_id}")
                
                # Check employees referencing this position
                res_emp = await db.execute(select(Employee).where(Employee.position_id == pos_id))
                emps = res_emp.scalars().all()
                print(f"  Employees referencing this position as primary (Employee.position_id): {[(e.id, e.employee_code, e.name) for e in emps]}")
                
                # If Position has employee_id, show that employee's primary position
                if p.employee_id:
                    emp_direct = await db.get(Employee, p.employee_id)
                    if emp_direct:
                        print(f"  Direct employee's primary position ID (Employee.position_id): {emp_direct.position_id}")
            else:
                print(f"=== POSITION {pos_id} not found ===")

asyncio.run(run_inspection())
