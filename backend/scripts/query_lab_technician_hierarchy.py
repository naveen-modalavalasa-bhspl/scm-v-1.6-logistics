"""Query Lab Technician employees and trace their hierarchy upwards.

Hierarchy: LAB TECHNICIAN -> OE -> DISTRICT MANAGER -> REGIONAL MANAGER -> SPH

Looks up positions by matching on position name (case-insensitive).
Traces parent_position_id chain upward and lists ALL employees at each level.
Also takes exactly 3 Lab Technician employees and shows their full hierarchy.
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings


async def get_employees_for_positions(db, position_ids):
    """Get all employees whose position_id is in the given list of position ids."""
    from app.models.settings_master import Employee
    if not position_ids:
        return []
    q = select(Employee).where(
        Employee.position_id.in_(position_ids)
    ).order_by(Employee.name)
    res = await db.execute(q)
    return res.scalars().all()


async def get_employee_by_id(db, employee_id):
    from app.models.settings_master import Employee
    q = select(Employee).where(Employee.id == employee_id)
    res = await db.execute(q)
    return res.scalar_one_or_none()


def sep(char="=", width=80):
    print()
    print(char * width)
    print()


async def main():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    
    async with AsyncSession(engine) as db:
        from app.models.settings_master import Position, Employee
        
        hierarchy_names = [
            "LAB TECHNICIAN",
            "OE",
            "DISTRICT MANAGER",
            "REGIONAL MANAGER",
            "SPH",
        ]
        
        print("=" * 80)
        print("  HIERARCHY QUERY: %s" % (" -> ".join(hierarchy_names)))
        print("  Timestamp: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print("=" * 80)
        
        positions_found = {}
        for name in hierarchy_names:
            q = select(Position).where(Position.name.ilike("%%%s%%" % name)).order_by(Position.name)
            res = await db.execute(q)
            positions = res.scalars().all()
            positions_found[name] = positions
            
            print()
            print("-" * 80)
            print("  POSITIONS matching '%s': %d found" % (name, len(positions)))
            print("-" * 80)
            for p in positions:
                parent_info = ""
                if p.parent_position_id:
                    parent_q = select(Position.name).where(Position.id == p.parent_position_id)
                    parent_res = await db.execute(parent_q)
                    parent_name = parent_res.scalar_one_or_none()
                    parent_info = "  parent: %s (id=%s)" % (parent_name, p.parent_position_id)
                
                emp_info = ""
                if p.employee_id:
                    emp = await get_employee_by_id(db, p.employee_id)
                    emp_info = "  [assigned emp: %s]" % (emp.name if emp else str(p.employee_id))
                
                print("    id=%-6d name='%s'%s" % (p.id, p.name, emp_info))
                print("           code='%s'  role_id=%s  level='%s'  %s" % (p.code, p.role_id, p.level_name, parent_info))
        
        lab_tech_positions = positions_found.get("LAB TECHNICIAN", [])
        if not lab_tech_positions:
            print()
            print("WARNING: No Lab Technician positions found in the database.")
            print("   Searched using: Position.name ILIKE '%%LAB TECHNICIAN%%'")
            print()
            print("   Showing ALL position names in DB for reference:")
            all_pos_q = select(Position.id, Position.name, Position.parent_position_id).order_by(Position.name).limit(200)
            all_pos = await db.execute(all_pos_q)
            for pid, pname, ppid in all_pos.all():
                print("     id=%-5d name='%s' parent_id=%s" % (pid, pname, ppid))
            await engine.dispose()
            return
        
        for lt_pos in lab_tech_positions[:3]:
            sep("-")
            print()
            print("  *** HIERARCHY CHAIN starting from: %s (id=%d)" % (lt_pos.name, lt_pos.id))
            print("    Code: %s | Role ID: %s | Level: %s" % (lt_pos.code, lt_pos.role_id, lt_pos.level_name))
            
            lt_employees = await get_employees_for_positions(db, [lt_pos.id])
            if lt_pos.employee_id:
                emp = await get_employee_by_id(db, lt_pos.employee_id)
                if emp and emp not in lt_employees:
                    lt_employees = list(lt_employees) + [emp]
            
            print()
            print("  >> Level 1 - %s:" % lt_pos.name)
            if lt_employees:
                for emp in lt_employees:
                    print("      - %s - %s (email: %s, phone: %s)" % (emp.employee_code, emp.name, emp.email or '', emp.phone or ''))
            else:
                print("      - No employees directly assigned")
            
            chain = []
            curr_id = lt_pos.parent_position_id
            level = 2
            while curr_id:
                q = select(Position).where(Position.id == curr_id)
                res = await db.execute(q)
                pos = res.scalar_one_or_none()
                if not pos:
                    break
                
                chain.append(pos)
                
                emp_list = await get_employees_for_positions(db, [pos.id])
                if pos.employee_id:
                    emp = await get_employee_by_id(db, pos.employee_id)
                    if emp and emp not in emp_list:
                        emp_list = list(emp_list) + [emp]
                
                print()
                print("  >> Level %d - %s (id=%d, parent_id=%s):" % (level, pos.name, pos.id, pos.parent_position_id))
                if emp_list:
                    for emp in emp_list:
                        print("      - %s - %s (email: %s, phone: %s)" % (emp.employee_code, emp.name, emp.email or '', emp.phone or ''))
                else:
                    print("      - No employees directly assigned")
                
                curr_id = pos.parent_position_id
                level += 1
            
            if not chain:
                print("      - No parent positions found (may be at top of hierarchy)")
        
        sep("#")
        print("  COMPREHENSIVE HIERARCHY REPORT")
        print("  All positions matching the chain and their employees")
        sep("#")
        
        searched_names = hierarchy_names
        
        all_levels = []
        for name in searched_names:
            matching = positions_found.get(name, [])
            for pos in matching:
                emp_list = await get_employees_for_positions(db, [pos.id])
                if pos.employee_id:
                    emp = await get_employee_by_id(db, pos.employee_id)
                    if emp and emp not in emp_list:
                        emp_list = list(emp_list) + [emp]
                
                parent_name = ""
                if pos.parent_position_id:
                    pn_q = select(Position.name).where(Position.id == pos.parent_position_id)
                    pn_res = await db.execute(pn_q)
                    parent_name = pn_res.scalar_one_or_none() or ""
                
                all_levels.append({
                    "level_name": name,
                    "position": pos,
                    "parent_name": parent_name,
                    "employees": emp_list,
                })
        
        print()
        print("%-30s %-20s %-6s %-30s" % ("POSITION", "CODE", "#EMPS", "PARENT"))
        print("%s  %s  %s  %s" % ("-"*30, "-"*20, "-"*6, "-"*30))
        for lvl in all_levels:
            emp_count = len(lvl["employees"])
            print("%-30s %-20s %-6d %-30s" % (lvl['position'].name, lvl['position'].code, emp_count, lvl['parent_name']))
            for emp in lvl["employees"]:
                print("  |_ %-15s %s" % (emp.employee_code, emp.name))
        
        sep("*")
        print("  3 LAB TECHNICIAN EMPLOYEES -- FULL HIERARCHY TREES")
        sep("*")
        
        lt_all_employees = []
        for pos in lab_tech_positions:
            emps = await get_employees_for_positions(db, [pos.id])
            lt_all_employees.extend(emps)
            if pos.employee_id:
                emp = await get_employee_by_id(db, pos.employee_id)
                if emp and emp not in lt_all_employees:
                    lt_all_employees.append(emp)
        
        if not lt_all_employees:
            print()
            print("  No Lab Technician employees found.")
            print()
            print("  Checking all records for 'STORE', 'KEEPER', etc...")
            seen_ids = set()
            for search_term in ["STORE", "KEEPER", "TECHNICIAN", "LAB"]:
                q = select(Employee).where(
                    Employee.name.ilike("%%%s%%" % search_term)
                    | Employee.employee_code.ilike("%%%s%%" % search_term)
                ).order_by(Employee.name).limit(20)
                res = await db.execute(q)
                emps = res.scalars().all()
                for emp in emps:
                    if emp.id not in seen_ids:
                        seen_ids.add(emp.id)
                        pos_name = ""
                        if emp.position_id:
                            pn_q = select(Position.name).where(Position.id == emp.position_id)
                            pn_res = await db.execute(pn_q)
                            pos_name = pn_res.scalar_one_or_none() or ""
                        print("    - %-15s %-30s position_id=%s pos='%s'" % (emp.employee_code, emp.name, emp.position_id, pos_name))
        else:
            three_emps = lt_all_employees[:3]
            
            for idx, emp in enumerate(three_emps, 1):
                print()
                print("  +=== Employee #%d: %s - %s ===+" % (idx, emp.employee_code, emp.name))
                
                if emp.position_id:
                    q = select(Position).where(Position.id == emp.position_id)
                    res = await db.execute(q)
                    emp_pos = res.scalar_one_or_none()
                else:
                    emp_pos = None
                
                if not emp_pos:
                    print("  |  No position assigned.")
                    print("  +=============================================+")
                    continue
                
                print("  |  Position: %s (id=%d)" % (emp_pos.name, emp_pos.id))
                print("  |")
                
                chain = []
                curr_id = emp_pos.id
                while curr_id:
                    q = select(Position).where(Position.id == curr_id)
                    res = await db.execute(q)
                    pos = res.scalar_one_or_none()
                    if not pos:
                        break
                    chain.append(pos)
                    curr_id = pos.parent_position_id
                
                for i, pos in enumerate(chain):
                    prefix = "  |  " if i < len(chain) - 1 else "  +--"
                    arrow = " --> " if i > 0 else "      "
                    
                    emps_at_pos = await get_employees_for_positions(db, [pos.id])
                    if pos.employee_id:
                        e = await get_employee_by_id(db, pos.employee_id)
                        if e and e not in emps_at_pos:
                            emps_at_pos = list(emps_at_pos) + [e]
                    
                    if i == 0:
                        print("  %s %s %-25s (YOU ARE HERE)" % (prefix, arrow, pos.name))
                    else:
                        print("  %s %s %-25s (id=%d)" % (prefix, arrow, pos.name, pos.id))
                    
                    for e in emps_at_pos:
                        marker = " <-- YOU" if e.id == emp.id else ""
                        print("  %s       %-15s %s%s" % (prefix, e.employee_code, e.name, marker))
                    
                    if emps_at_pos:
                        print("  %s" % prefix)
                
                print()
        
        sep("O")
        print("  ALL EMPLOYEES AT EACH HIERARCHY LEVEL")
        sep("O")
        
        for name in searched_names:
            matching = positions_found.get(name, [])
            if not matching:
                continue
            
            print()
            print("  +--- %s ---+" % name)
            for pos in matching:
                emps = await get_employees_for_positions(db, [pos.id])
                if pos.employee_id:
                    e = await get_employee_by_id(db, pos.employee_id)
                    if e and e not in emps:
                        emps = list(emps) + [e]
                
                print("  | Position: %-30s (code: %s)" % (pos.name, pos.code))
                if emps:
                    for e in emps:
                        print("  |   +- %-15s %-30s %-25s %s" % (e.employee_code, e.name, e.email or '', e.phone or ''))
                else:
                    print("  |   +- (No employees assigned)")
                print("  +---------------------------------------------+")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
