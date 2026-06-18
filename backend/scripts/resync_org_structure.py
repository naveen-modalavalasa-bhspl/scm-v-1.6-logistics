"""
Comprehensive Organisation Structure Re-Sync Script.

DROPs and re-CREATES tables (positions, employees, offices, projects) so the
schema matches the SQLAlchemy models exactly, then re-populates all data from
the HRMS external API. Captures ALL fields from the API and ensures BOTH
Position.employee_id AND Employee.position_id are set consistently.

Usage (server):
    cd /home/ubuntu/erp/backend
    python3 -m scripts.resync_org_structure

Usage (local):
    cd backend
    python -m scripts.resync_org_structure
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import text

from app.config import settings
from app.database import engine, AsyncSessionLocal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(row: dict, *keys, max_len=255):
    for key in keys:
        val = row
        for part in key.split("."):
            if not isinstance(val, dict):
                val = None
                break
            val = val.get(part)
        if val is not None and not isinstance(val, (dict, list)) and str(val).strip():
            return str(val).strip()[:max_len]
    return None


def _date(val):
    if not val:
        return None
    try:
        return str(val)[:10]
    except Exception:
        return None


def _int(val):
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _pos_base_url():
    base = settings.HR_EMPLOYEE_API_URL
    if "/api/employees" in base:
        return base.replace("/api/employees", "/api/positions")
    elif "/employees" in base:
        return base.replace("/employees", "/positions")
    return base.replace("employees", "positions")


# ---------------------------------------------------------------------------
# Step 1 — DROP & re-CREATE tables
# ---------------------------------------------------------------------------

async def drop_and_recreate_tables():
    """DROP and re-CREATE tables so schema matches models exactly."""
    print("[1/5] Dropping and recreating tables...")
    from app.models.master import Office, Position, Employee
    from app.models.user import Project

    async with engine.connect() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ("positions", "employees", "offices", "projects"):
            await conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
            print(f"  Dropped {table}")
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        await conn.commit()

    async with engine.begin() as conn:
        await conn.run_sync(Project.__table__.create)
        await conn.run_sync(Office.__table__.create)
        await conn.run_sync(Position.__table__.create)
        await conn.run_sync(Employee.__table__.create)
        print("  Recreated all tables with current model schema")


# ---------------------------------------------------------------------------
# Step 2 — Fetch all data from HRMS API
# ---------------------------------------------------------------------------

async def _fetch_all_paginated(client, headers, base_url, label):
    all_rows = []
    page = 1
    while True:
        url = f"{base_url}?page_size=200&page={page}"
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            print(f"  Error {label} page {page}: {e}")
            break
        items = payload.get("results") or payload.get("items") or []
        if not items:
            break
        all_rows.extend(items)
        if not payload.get("next"):
            break
        page += 1
        await asyncio.sleep(0.03)
    return all_rows


async def fetch_all(client, headers):
    print("[2/5] Fetching employees from HRMS API...")
    employee_rows = await _fetch_all_paginated(client, headers,
                                               settings.HR_EMPLOYEE_API_URL,
                                               "employees")
    print(f"  Total: {len(employee_rows)} employees\n")

    print("[3/5] Fetching positions from HRMS API...")
    position_rows = await _fetch_all_paginated(client, headers,
                                               _pos_base_url(), "positions")
    print(f"  Total: {len(position_rows)} positions\n")
    return employee_rows, position_rows


# ---------------------------------------------------------------------------
# Step 4 — Sync data into the freshly created tables
# ---------------------------------------------------------------------------

async def sync_all(db, employee_rows, position_rows, org_id):
    print("[4/5] Syncing projects, offices, positions, employees...")
    stats = {"projects": 0, "offices": 0, "positions": 0, "employees": 0}

    # ---- PROJECTS ----
    project_map = {}
    for row in employee_rows:
        proj = row.get("project") or {}
        code = (_text(proj, "code") or "").upper()
        name = _text(proj, "name") or code
        if code and code not in project_map:
            existing = (await db.execute(
                text("SELECT id FROM projects WHERE code = :code"),
                {"code": code}
            )).scalar_one_or_none()
            if existing:
                project_map[code] = existing
            else:
                r = await db.execute(
                    text("""INSERT INTO projects (organization_id, name, code, status, created_at, updated_at)
                            VALUES (:org_id, :name, :code, 'active', NOW(), NOW())"""),
                    {"org_id": org_id, "name": name, "code": code}
                )
                project_map[code] = r.lastrowid
                stats["projects"] += 1
    await db.commit()
    print(f"  Projects: {stats['projects']} created, {len(project_map)} total")

    # ---- OFFICES ----
    office_map = {}
    for row in employee_rows:
        off = row.get("office") or {}
        name = _text(off, "name")
        if not name:
            continue
        key = name.lower().strip()
        if key in office_map:
            continue
        geo = off.get("geo_location") or {}
        existing = (await db.execute(
            text("SELECT id FROM offices WHERE LOWER(name) = :name"),
            {"name": key}
        )).scalar_one_or_none()
        if existing:
            office_map[key] = existing
        else:
            r = await db.execute(
                text("""INSERT INTO offices (name, level, country, state, district, mandal,
                         cluster, cluster_type, specific_location, address,
                         created_at, updated_at)
                        VALUES (:name, :level, :country, :state, :district, :mandal,
                                :cluster, :cluster_type, :specific_location, :address,
                                NOW(), NOW())"""),
                {"name": name, "level": _text(off, "level"),
                 "country": _text(geo, "country"), "state": _text(geo, "state"),
                 "district": _text(geo, "district"), "mandal": _text(geo, "mandal"),
                 "cluster": _text(geo, "cluster"), "cluster_type": _text(geo, "cluster_type"),
                 "specific_location": _text(geo, "specific_location"),
                 "address": _text(geo, "address", max_len=2000)}
            )
            office_map[key] = r.lastrowid
            stats["offices"] += 1
    await db.commit()
    print(f"  Offices: {stats['offices']} created, {len(office_map)} total")

    # ---- POSITIONS (from employee data) ----
    position_map = {}
    parent_refs = []

    for row in employee_rows:
        pos = row.get("position") or {}
        code = (_text(pos, "code") or "").upper()
        name = _text(pos, "name")
        if not code or not name or code in position_map:
            continue

        project_code = (_text(row.get("project") or {}, "code") or "").upper()
        office_name = (_text(row.get("office") or {}, "name") or "").lower().strip()
        project_id = project_map.get(project_code)
        office_id = office_map.get(office_name)

        reporting_to = pos.get("reporting_to") or []
        parent_code = None
        if reporting_to and isinstance(reporting_to, list) and len(reporting_to) > 0:
            rt = reporting_to[0]
            if isinstance(rt, dict):
                parent_code = (_text(rt, "code") or "").upper()

        existing = (await db.execute(
            text("SELECT id FROM positions WHERE code = :code"),
            {"code": code}
        )).scalar_one_or_none()

        if existing:
            position_map[code] = existing
        else:
            role_details = pos.get("role_details") or {}
            try:
                r = await db.execute(
                    text("""INSERT INTO positions
                        (name, code, role_name, role_id, level_name, level_rank,
                         department, section, job_name, job_family_name, job_family_id,
                         role_type_id, status, start_date, project_id, office_id,
                         created_at, updated_at)
                        VALUES (:name, :code, :role_name, :role_id, :level_name, :level_rank,
                                :department, :section, :job_name, :job_family_name, :job_family_id,
                                :role_type_id, :status, :start_date, :project_id, :office_id,
                                NOW(), NOW())"""),
                    {"name": name, "code": code,
                     "role_name": _text(pos, "role_name") or _text(role_details, "name"),
                     "role_id": _int(pos.get("role_id")) or _int(role_details.get("id")),
                     "level_name": _text(pos, "level_name") or _text(pos, "level"),
                     "level_rank": _int(pos.get("level_rank")),
                     "department": _text(pos, "department") or _text(row, "department"),
                     "section": _text(pos, "section"),
                     "job_name": _text(pos, "job_name") or _text(role_details, "job_name"),
                     "job_family_name": _text(pos, "job_family_name"),
                     "job_family_id": _int(pos.get("job_family_id")),
                     "role_type_id": _int(pos.get("role_type_id")),
                     "status": _text(pos, "status") or "active",
                     "start_date": _date(pos.get("start_date")),
                     "project_id": project_id, "office_id": office_id}
                )
                position_map[code] = r.lastrowid
                stats["positions"] += 1
                if parent_code:
                    parent_refs.append((code, parent_code))
            except Exception as e:
                print(f"  WARN: Could not create position {code}: {e}")

    # Parent links
    for child_code, parent_code in parent_refs:
        child_id = position_map.get(child_code)
        parent_id = position_map.get(parent_code)
        if child_id and parent_id and child_id != parent_id:
            try:
                await db.execute(
                    text("UPDATE positions SET parent_position_id = :pid WHERE id = :cid AND parent_position_id IS NULL"),
                    {"cid": child_id, "pid": parent_id}
                )
            except Exception:
                pass

    # Positions from positions API for missed ones
    for pos_row in position_rows:
        code = (_text(pos_row, "code") or "").upper()
        if not code or code in position_map:
            continue
        name = _text(pos_row, "name") or code
        role_details = pos_row.get("role_details") or {}
        try:
            r = await db.execute(
                text("""INSERT INTO positions
                    (name, code, role_name, role_id, level_name, level_rank,
                     department, section, job_name, job_family_name, job_family_id,
                     role_type_id, status, start_date, created_at, updated_at)
                    VALUES (:name, :code, :role_name, :role_id, :level_name, :level_rank,
                            :department, :section, :job_name, :job_family_name, :job_family_id,
                            :role_type_id, :status, :start_date, NOW(), NOW())"""),
                {"name": name, "code": code,
                 "role_name": _text(pos_row, "role_name") or _text(role_details, "name"),
                 "role_id": _int(pos_row.get("role_id")) or _int(role_details.get("id")),
                 "level_name": _text(pos_row, "level_name") or _text(pos_row, "level"),
                 "level_rank": _int(pos_row.get("level_rank")),
                 "department": _text(pos_row, "department_name") or _text(pos_row, "department"),
                 "section": _text(pos_row, "section_name") or _text(pos_row, "section"),
                 "job_name": _text(pos_row, "job_name") or _text(role_details, "job_name"),
                 "job_family_name": _text(pos_row, "job_family_name"),
                 "job_family_id": _int(pos_row.get("job_family_id")),
                 "role_type_id": _int(pos_row.get("role_type_id")),
                 "status": _text(pos_row, "status") or "active",
                 "start_date": _date(pos_row.get("start_date"))}
            )
            position_map[code] = r.lastrowid
            stats["positions"] += 1
        except Exception as e:
            print(f"  WARN: Could not insert position {code}: {e}")

    await db.commit()
    print(f"  Positions: {stats['positions']} created, {len(position_map)} total")

    # ---- EMPLOYEES (bidirectional mapping) ----
    for row in employee_rows:
        emp = row.get("employee") or {}
        code = (_text(emp, "employee_code") or _text(row, "employee_code")
                or _text(emp, "code") or "")
        name = _text(emp, "name") or _text(row, "name") or code
        if not code:
            continue

        pos_data = row.get("position") or {}
        pos_code = (_text(pos_data, "code") or "").upper()
        position_id = position_map.get(pos_code)

        existing = (await db.execute(
            text("SELECT id FROM employees WHERE employee_code = :code"),
            {"code": code}
        )).scalar_one_or_none()

        if not existing:
            try:
                r = await db.execute(
                    text("""INSERT INTO employees
                        (employee_code, name, photo, status, dob, gender,
                         pan_number, aadhaar_number, email, phone,
                         hire_date, bank_details, position_id, created_at, updated_at)
                        VALUES (:code, :name, :photo, :status, :dob, :gender,
                                :pan, :aadhaar, :email, :phone,
                                :hired, :bank_details, :pos_id, NOW(), NOW())"""),
                    {"code": code, "name": name,
                     "photo": _text(emp, "photo"),
                     "status": _text(emp, "status") or "Active",
                     "dob": _date(emp.get("dob")),
                     "gender": _text(emp, "gender"),
                     "pan": _text(emp, "pan_number"),
                     "aadhaar": _text(emp, "aadhaar_number"),
                     "email": _text(emp, "email"),
                     "phone": _text(emp, "phone"),
                     "hired": _date(row.get("hire_date")),
                     "bank_details": row.get("bank_details"),
                     "pos_id": position_id}
                )
                emp_id = r.lastrowid
                stats["employees"] += 1

                if position_id and emp_id:
                    await db.execute(
                        text("UPDATE positions SET employee_id = :eid WHERE id = :pid AND employee_id IS NULL"),
                        {"pid": position_id, "eid": emp_id}
                    )
            except Exception as e:
                print(f"  WARN: Could not create employee {code}: {e}")
        else:
            emp_id = existing
            try:
                await db.execute(
                    text("""UPDATE employees SET name=:name, photo=:photo, status=:status,
                            dob=:dob, gender=:gender, pan_number=:pan, aadhaar_number=:aadhaar,
                            email=:email, phone=:phone, position_id=:pos_id, updated_at=NOW()
                            WHERE id=:id"""),
                    {"id": emp_id, "name": name, "photo": _text(emp, "photo"),
                     "status": _text(emp, "status") or "Active",
                     "dob": _date(emp.get("dob")), "gender": _text(emp, "gender"),
                     "pan": _text(emp, "pan_number"), "aadhaar": _text(emp, "aadhaar_number"),
                     "email": _text(emp, "email"), "phone": _text(emp, "phone"),
                     "pos_id": position_id}
                )
            except Exception as e:
                print(f"  WARN: Could not update employee {code}: {e}")

    await db.commit()

    # Step 5 — Assigned employee from positions API
    print("\n[5/5] Applying assigned_employee from positions API...")
    mapped = 0
    for pos_row in position_rows:
        code = (_text(pos_row, "code") or "").upper()
        if not code:
            continue
        assigned = pos_row.get("assigned_employee")
        if not assigned or not isinstance(assigned, dict):
            continue
        emp_id = _int(assigned.get("id"))
        if not emp_id:
            continue
        pos_id = position_map.get(code)
        if not pos_id:
            continue
        try:
            await db.execute(
                text("UPDATE positions SET employee_id = :eid WHERE id = :pid"),
                {"pid": pos_id, "eid": emp_id}
            )
            mapped += 1
        except Exception:
            pass
    await db.commit()
    print(f"  Mapped {mapped} positions via assigned_employee.\n")

    # Summary
    print("=" * 60)
    print("RE-SYNC COMPLETE")
    print("=" * 60)
    print(f"  Projects:  {stats['projects']} created")
    print(f"  Offices:   {stats['offices']} created")
    print(f"  Positions: {stats['positions']} created ({len(position_map)} total)")
    print(f"  Employees: {stats['employees']} total")
    print(f"  Mapped:    {mapped} via assigned_employee")
    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("BHSPL ORG STRUCTURE RE-SYNC")
    print("=" * 60)
    print(f"Time:  {datetime.now(timezone.utc).isoformat()}")
    print(f"DB:    {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    print(f"API:   {settings.HR_EMPLOYEE_API_URL}\n")

    if not settings.HR_EMPLOYEE_API_URL or not settings.HR_API_KEY:
        print("ERROR: Set HR_EMPLOYEE_API_URL and HR_API_KEY in .env")
        sys.exit(1)

    headers = {"X-Api-Key": settings.HR_API_KEY, "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=settings.HR_API_TIMEOUT,
                                  follow_redirects=True) as client:
        await drop_and_recreate_tables()
        employee_rows, position_rows = await fetch_all(client, headers)

        if not employee_rows:
            print("ERROR: No employees fetched. Aborting.")
            sys.exit(1)

        async with AsyncSessionLocal() as db:
            await sync_all(db, employee_rows, position_rows, org_id=1)

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
