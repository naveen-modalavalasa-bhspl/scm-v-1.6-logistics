"""Trace the exact parent_position_id chain for 3 Lab Technicians and
show ALL hierarchy positions with employees mapped to them.

Hierarchy: LAB TECHNICIAN -> OE -> DISTRICT MANAGER -> REGIONAL MANAGER -> SPH
"""

import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def get_employees_at_position(db, position_id):
    from app.models.settings_master import Employee
    q = select(Employee).where(Employee.position_id == position_id).order_by(Employee.name)
    res = await db.execute(q)
    return list(res.scalars().all())


def fmt_emp(emp):
    return "%-15s %s" % (emp.employee_code or '', emp.name or '')


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with AsyncSession(engine) as db:
        from app.models.settings_master import Position

        # ===== 1. EXACT CHAIN TRACE for 3 Lab Techs under TIRUPATHI =====
        lab_tech_ids = [2810, 2811, 2812]  # Ravi Kumar, Rajesh, Chaitanya
        
        print("=" * 90)
        print("  PART 1: EXACT parent_position_id CHAIN TRACE")
        print("=" * 90)
        
        for lt_id in lab_tech_ids:
            q = select(Position).where(Position.id == lt_id)
            res = await db.execute(q)
            lt = res.scalar_one_or_none()
            if not lt:
                continue
            
            # Get employee
            emps = await get_employees_at_position(db, lt.id)
            
            # Trace full chain
            chain = []
            curr_id = lt.id
            while curr_id:
                q = select(Position).where(Position.id == curr_id)
                res = await db.execute(q)
                pos = res.scalar_one_or_none()
                if not pos:
                    break
                
                chain_emps = await get_employees_at_position(db, pos.id)
                chain.append((pos, chain_emps))
                curr_id = pos.parent_position_id
            
            print()
            print("--- Employee: %s ---" % (emps[0].name if emps else '?'))
            print()
            for i, (pos, pos_emps) in enumerate(chain):
                indent = "  " * i
                arrow = " --> " if i > 0 else "      "
                emp_str = ", ".join(fmt_emp(e) for e in pos_emps) if pos_emps else "(no employee)"
                print("%s%s Level %d: %-50s [id=%d, parent_id=%s]" % (indent, arrow, i + 1, pos.name, pos.id, pos.parent_position_id))
                print("%s     %s" % (indent, emp_str))
        
        # ===== 2. ALL REGIONAL MANAGER positions (regardless of parent chain) =====
        print()
        print("=" * 90)
        print("  PART 2: ALL REGIONAL MANAGER POSITIONS with their employees")
        print("=" * 90)
        
        rm_q = select(Position).where(Position.name.ilike("%REGIONAL MANAGER%")).order_by(Position.name)
        rm_res = await db.execute(rm_q)
        rms = rm_res.scalars().all()
        
        print()
        print("%-5s %-55s %-25s %s" % ("ID", "Position Name", "Code", "Employees"))
        print("-" * 90)
        for rm in rms:
            emps = await get_employees_at_position(db, rm.id)
            # Also check Position.employee_id
            if rm.employee_id:
                from app.models.settings_master import Employee
                eq = select(Employee).where(Employee.id == rm.employee_id)
                er = await db.execute(eq)
                e = er.scalar_one_or_none()
                if e and e not in emps:
                    emps.append(e)
            
            if emps:
                emp_names = "; ".join("%s (%s)" % (e.name, e.employee_code or '') for e in emps)
            else:
                emp_names = "(no employee)"
            
            print("%-5d %-55s %-25s %s" % (rm.id, rm.name[:55], rm.code[:25], emp_names))
            
            # Show its parent too
            if rm.parent_position_id:
                pp = await db.execute(select(Position.name).where(Position.id == rm.parent_position_id))
                pp_name = pp.scalar_one_or_none() or '?'
                print("      parent_position_id=%d -> %s" % (rm.parent_position_id, pp_name))
            print()

        # ===== 3. ALL SPH positions =====
        print("=" * 90)
        print("  PART 3: ALL SPH POSITIONS with their employees")
        print("=" * 90)
        
        sph_q = select(Position).where(Position.name.ilike("%SPH%")).order_by(Position.name)
        sph_res = await db.execute(sph_q)
        sphs = sph_res.scalars().all()
        
        print()
        print("%-5s %-55s %-25s %s" % ("ID", "Position Name", "Code", "Employees"))
        print("-" * 90)
        for sph in sphs:
            emps = await get_employees_at_position(db, sph.id)
            if sph.employee_id:
                from app.models.settings_master import Employee
                eq = select(Employee).where(Employee.id == sph.employee_id)
                er = await db.execute(eq)
                e = er.scalar_one_or_none()
                if e and e not in emps:
                    emps.append(e)
            
            if emps:
                emp_names = "; ".join("%s (%s)" % (e.name, e.employee_code or '') for e in emps)
            else:
                emp_names = "(no employee)"
            
            print("%-5d %-55s %-25s %s" % (sph.id, sph.name[:55], sph.code[:25], emp_names))
            if sph.parent_position_id:
                pp = await db.execute(select(Position.name).where(Position.id == sph.parent_position_id))
                pp_name = pp.scalar_one_or_none() or '?'
                print("      parent -> %s" % pp_name)
            print()

        # ===== 4. ALL DISTRICT MANAGER positions =====
        print("=" * 90)
        print("  PART 4: ALL DISTRICT MANAGER POSITIONS with their employees")
        print("=" * 90)
        
        dm_q = select(Position).where(Position.name.ilike("%DISTRICT MANAGER%")).order_by(Position.name)
        dm_res = await db.execute(dm_q)
        dms = dm_res.scalars().all()
        
        print()
        print("%-5s %-55s %-25s %s" % ("ID", "Position Name", "Code", "Employees"))
        print("-" * 90)
        for dm in dms:
            emps = await get_employees_at_position(db, dm.id)
            if dm.employee_id:
                from app.models.settings_master import Employee
                eq = select(Employee).where(Employee.id == dm.employee_id)
                er = await db.execute(eq)
                e = er.scalar_one_or_none()
                if e and e not in emps:
                    emps.append(e)
            
            if emps:
                emp_names = "; ".join("%s (%s)" % (e.name, e.employee_code or '') for e in emps)
            else:
                emp_names = "(no employee)"
            
            print("%-5d %-55s %-25s %s" % (dm.id, dm.name[:55], dm.code[:25], emp_names))
            if dm.parent_position_id:
                pp = await db.execute(select(Position.name).where(Position.id == dm.parent_position_id))
                pp_name = pp.scalar_one_or_none() or '?'
                print("      parent -> %s" % pp_name)
            print()
        
        # ===== 5. ALL OE positions =====
        print("=" * 90)
        print("  PART 5: ALL OE POSITIONS with their employees")
        print("=" * 90)
        
        oe_q = select(Position).where(Position.name.ilike("OE%")).order_by(Position.name)
        oe_res = await db.execute(oe_q)
        oes = oe_res.scalars().all()
        
        print()
        print("%-5s %-60s %-25s %s" % ("ID", "Position Name", "Code", "Employees"))
        print("-" * 90)
        for oe in oes:
            emps = await get_employees_at_position(db, oe.id)
            if oe.employee_id:
                from app.models.settings_master import Employee
                eq = select(Employee).where(Employee.id == oe.employee_id)
                er = await db.execute(eq)
                e = er.scalar_one_or_none()
                if e and e not in emps:
                    emps.append(e)
            
            if emps:
                emp_names = "; ".join("%s (%s)" % (e.name, e.employee_code or '') for e in emps)
            else:
                emp_names = "(no employee)"
            
            print("%-5d %-60s %-25s %s" % (oe.id, oe.name[:60], oe.code[:25], emp_names))
            if oe.parent_position_id:
                pp = await db.execute(select(Position.name).where(Position.id == oe.parent_position_id))
                pp_name = pp.scalar_one_or_none() or '?'
                print("      parent -> %s" % pp_name)
            print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
