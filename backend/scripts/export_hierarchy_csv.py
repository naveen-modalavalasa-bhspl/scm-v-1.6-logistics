"""Export the complete LAB TECHNICIAN -> OE -> DISTRICT MANAGER -> REGIONAL MANAGER -> SPH
hierarchy as a CSV file, with each position and its employees mapped.

Output: hierarchy_export.csv in the project root.
"""

import asyncio
import csv
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    all_rows = []

    async with AsyncSession(engine) as db:
        from app.models.settings_master import Position, Employee

        # Query ALL positions that belong to the hierarchy chain
        # The hierarchy levels we care about
        level_filters = [
            ("LAB TECHNICIAN", Position.name.ilike("%LAB TECHNICIAN%")),
            ("OE", Position.name.ilike("OE%")),
            ("DISTRICT MANAGER", Position.name.ilike("%DISTRICT MANAGER%")),
            ("REGIONAL MANAGER", Position.name.ilike("%REGIONAL MANAGER%")),
            ("SPH", Position.name.ilike("%SPH%")),
        ]

        total_exported = 0

        for level_name, filter_clause in level_filters:
            q = select(Position).where(filter_clause).order_by(Position.name)
            res = await db.execute(q)
            positions = res.scalars().all()

            for pos in positions:
                # Get employees at this position (via Employee.position_id)
                emp_q = select(Employee).where(Employee.position_id == pos.id).order_by(Employee.name)
                emp_res = await db.execute(emp_q)
                emps = list(emp_res.scalars().all())

                # Also check Position.employee_id (direct assign)
                if pos.employee_id:
                    eq = select(Employee).where(Employee.id == pos.employee_id)
                    er = await db.execute(eq)
                    e = er.scalar_one_or_none()
                    if e and e not in emps:
                        emps.append(e)

                # Get parent name
                parent_name = ""
                if pos.parent_position_id:
                    pn_q = select(Position.name).where(Position.id == pos.parent_position_id)
                    pn_res = await db.execute(pn_q)
                    parent_name = pn_res.scalar_one_or_none() or ""

                # Get role name
                role_name = pos.role_name or ""
                if pos.role_id:
                    from app.models.user import Role
                    r_q = select(Role.name).where(Role.id == pos.role_id)
                    r_res = await db.execute(r_q)
                    r_name = r_res.scalar_one_or_none()
                    if r_name:
                        role_name = r_name

                if emps:
                    for emp in emps:
                        all_rows.append({
                            "Hierarchy Level": level_name,
                            "Position ID": pos.id,
                            "Position Name": pos.name,
                            "Position Code": pos.code,
                            "Role Name": role_name,
                            "Level Name": pos.level_name or "",
                            "Department": pos.department or "",
                            "Parent Position ID": pos.parent_position_id or "",
                            "Parent Position Name": parent_name,
                            "Employee ID": emp.id,
                            "Employee Code": emp.employee_code or "",
                            "Employee Name": emp.name or "",
                            "Email": emp.email or "",
                            "Phone": emp.phone or "",
                            "Status": emp.status or "",
                        })
                        total_exported += 1
                else:
                    # Still include positions with no assigned employees
                    all_rows.append({
                        "Hierarchy Level": level_name,
                        "Position ID": pos.id,
                        "Position Name": pos.name,
                        "Position Code": pos.code,
                        "Role Name": role_name,
                        "Level Name": pos.level_name or "",
                        "Department": pos.department or "",
                        "Parent Position ID": pos.parent_position_id or "",
                        "Parent Position Name": parent_name,
                        "Employee ID": "",
                        "Employee Code": "",
                        "Employee Name": "(no employee)",
                        "Email": "",
                        "Phone": "",
                        "Status": "",
                    })
                    total_exported += 1

    await engine.dispose()

    # Write CSV
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "hierarchy_export.csv")
    fieldnames = [
        "Hierarchy Level", "Position ID", "Position Name", "Position Code",
        "Role Name", "Level Name", "Department",
        "Parent Position ID", "Parent Position Name",
        "Employee ID", "Employee Code", "Employee Name",
        "Email", "Phone", "Status",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print("CSV exported: %s" % output_path)
    print("Total rows: %d" % total_exported)

    # Summary stats
    from collections import Counter
    level_counts = Counter(r["Hierarchy Level"] for r in all_rows)
    emp_counts = Counter(r["Hierarchy Level"] for r in all_rows if r["Employee Name"] and r["Employee Name"] != "(no employee)")
    print()
    print("Summary by hierarchy level:")
    print("%-25s %-10s %-10s" % ("Level", "Positions", "With Emp"))
    print("-" * 45)
    for level_name, _ in level_filters:
        total = level_counts.get(level_name, 0)
        filled = emp_counts.get(level_name, 0)
        print("%-25s %-10d %-10d" % (level_name, total, filled))
    print("-" * 45)
    print("%-25s %-10d %-10d" % ("TOTAL", sum(level_counts.values()), sum(emp_counts.values())))


if __name__ == "__main__":
    asyncio.run(main())
