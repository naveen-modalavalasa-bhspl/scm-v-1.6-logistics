import sys, pymysql
sys.path.insert(0, '.')
from app.config import settings

conn = pymysql.connect(
    host=settings.DB_HOST, port=settings.DB_PORT,
    user=settings.DB_USER, password=settings.DB_PASSWORD,
    database=settings.DB_NAME, charset='utf8mb4'
)
c = conn.cursor()

print("=" * 70)
print("1. OE ROLE INFO")
print("=" * 70)
c.execute("SELECT id, name, code FROM roles WHERE code LIKE '%OE%' OR name LIKE '%OE%' OR name LIKE '%OPERATION%EXECUTIVE%' OR code LIKE '%OPERATION%EXECUTIVE%'")
for row in c.fetchall():
    print(f"  Role: id={row[0]}, name='{row[1]}', code='{row[2]}'")

print()
print("=" * 70)
print("2. STORE KEEPER POSITION (3049)")
print("=" * 70)
c.execute("SELECT id, name, code, role_id, role_name, parent_position_id, employee_id FROM positions WHERE id = 3049")
row = c.fetchone()
if row:
    print(f"  id={row[0]}, name='{row[1]}', code='{row[2]}'")
    print(f"  role_id={row[3]}, role_name='{row[4]}'")
    print(f"  parent_position_id={row[5]}")
    print(f"  employee_id={row[6]}")
    
    # Get parent
    if row[5]:
        c.execute("SELECT id, name, code, role_id, role_name FROM positions WHERE id = %s", (row[5],))
        parent = c.fetchone()
        if parent:
            print(f"\n  PARENT position: id={parent[0]}, name='{parent[1]}', code='{parent[2]}'")
            print(f"  PARENT role_id={parent[3]}, role_name='{parent[4]}'")
            
            # Also check this parent's parent
            p2_id = parent[4] if len(parent) > 5 else None
            # Re-query with more columns
            c.execute("SELECT id, parent_position_id FROM positions WHERE id = %s", (parent[0],))
            p_full = c.fetchone()
            if p_full and p_full[1]:
                c.execute("SELECT id, name, code, role_id, role_name FROM positions WHERE id = %s", (p_full[1],))
                grandparent = c.fetchone()
                if grandparent:
                    print(f"\n  GRANDPARENT position: id={grandparent[0]}, name='{grandparent[1]}', code='{grandparent[2]}'")
                    print(f"  GRANDPARENT role_id={grandparent[3]}, role_name='{grandparent[4]}'")

print()
print("=" * 70)
print("3. ALL POSITIONS (OE-related)")
print("=" * 70)
c.execute("""
    SELECT p.id, p.name, p.code, p.role_id, r.name AS rname, r.code AS rcode,
           p.parent_position_id, p.employee_id
    FROM positions p
    LEFT JOIN roles r ON r.id = p.role_id
    WHERE r.code LIKE '%OE%' OR r.name LIKE '%OE%'
       OR r.name LIKE '%OPERATION%EXECUTIVE%'
       OR p.name LIKE '%OPERATION%EXEC%'
    ORDER BY p.name
""")
found_oe = c.fetchall()
if found_oe:
    print(f"  Found {len(found_oe)} OE-related positions:")
    for row in found_oe:
        print(f"    id={row[0]}, name='{row[1]}', code='{row[2]}'")
        print(f"      role_id={row[3]}, role_name='{row[4]}', role_code='{row[5]}'")
        print(f"      parent_position_id={row[6]}, employee_id={row[7]}")
else:
    print("  No OE position found! You need to create one.")

print()
print("=" * 70)
print("4. HR-EMP-07298 (OE/DM user) employee & position mapping")
print("=" * 70)
c.execute("""
    SELECT u.id AS user_id, u.username, u.employee_code, u.employee_id,
           u.active_role_id,
           e.id AS emp_id, e.employee_code AS emp_code,
           e.name AS emp_name, e.position_id,
           r.id AS role_id, r.name AS role_name, r.code AS role_code
    FROM users u
    LEFT JOIN employees e ON e.id = u.employee_id
    LEFT JOIN roles r ON r.id = u.active_role_id
    WHERE u.employee_code = 'HR-EMP-07298'
       OR u.username LIKE '%07298%'
""")
for row in c.fetchall():
    print(f"  User: id={row[0]}, username='{row[1]}', employee_code='{row[2]}'")
    print(f"  employee_id={row[3]}, active_role_id={row[4]}")
    print(f"  Emp: id={row[5]}, emp_code='{row[6]}', name='{row[7]}'")
    print(f"  Emp.position_id={row[8]}")
    print(f"  Active role: id={row[9]}, name='{row[10]}', code='{row[11]}'")
    
    # If position_id exists, check what position it is
    if row[8]:
        c.execute("SELECT id, name, code, role_id FROM positions WHERE id = %s", (row[8],))
        pos = c.fetchone()
        if pos:
            print(f"  Position: id={pos[0]}, name='{pos[1]}', code='{pos[2]}', role_id={pos[3]}")

print()
print("=" * 70)
print("5. PROJECT WORKFLOW CONFIG FOR PROJECT 23")
print("=" * 70)
c.execute("""
    SELECT pwc.project_id, pwc.role_id, r.name AS rname, r.code AS rcode,
           pwc.indent_approve, pwc.indent_view
    FROM project_workflow_configs pwc
    JOIN roles r ON r.id = pwc.role_id
    WHERE pwc.project_id = 23
    ORDER BY r.name
""")
for row in c.fetchall():
    print(f"  role_id={row[1]}, role='{row[2]}' ({row[3]}), indent_approve={row[4]}, indent_view={row[5]}")

print()
print("=" * 70)
print("6. RECOMMENDED SQL TO CREATE OE POSITION")
print("=" * 70)
print("""
-- If NO OE position exists at all, create one:
-- (Replace 'X' with the correct parent_position_id - the Div Manager position above Store Keeper)
-- 
-- Store Keeper (3049) currently has parent_position_id = 5880 (Div Manager)
-- We need: Store Keeper (3049) -> OE (NEW) -> Div Manager (5880)
--
-- So the new OE position's parent_position_id should be 5880
-- And Store Keeper (3049)'s parent_position_id should be updated to the NEW OE position's id

-- First, check if there's already a position we can re-use or if we need to insert one.
-- Also check positions table for the next available id.

-- If creating new:
-- INSERT INTO positions (id, name, code, role_id, role_name, parent_position_id, employee_id)
-- SELECT next_val, 'Operations Executive', 'OE', 18, 'OE', 5880, NULL
-- FROM (SELECT COALESCE(MAX(id), 0) + 1 AS next_val FROM positions) AS nv;
--
-- Then update Store Keeper's parent:
-- UPDATE positions SET parent_position_id = <NEW_OE_ID> WHERE id = 3049;

-- OR, if there's already a position with role_id=18 that just isn't linked:
-- UPDATE positions SET parent_position_id = <EXISTING_OE_ID> WHERE id = 3049;
""")

print()
print("=" * 70)
print("7. NEXT AVAILABLE POSITION ID + POSITIONS WITH role_id=18")
print("=" * 70)
c.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM positions")
next_id = c.fetchone()[0]
print(f"  Next available position id: {next_id}")

c.execute("SELECT id, name, code, parent_position_id FROM positions WHERE role_id = 18")
rows = c.fetchall()
if rows:
    print(f"  Existing positions with role_id=18:")
    for row in rows:
        print(f"    id={row[0]}, name='{row[1]}', code='{row[2]}', parent_id={row[3]}")
else:
    print("  No existing positions with role_id=18")

conn.close()
