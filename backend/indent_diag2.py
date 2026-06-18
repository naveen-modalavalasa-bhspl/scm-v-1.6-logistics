"""Additional diagnostics - check all projects with configs and positions data."""
import sys
sys.path.insert(0, '.')
import pymysql
from app.config import settings

conn = pymysql.connect(
    host=settings.DB_HOST, port=settings.DB_PORT,
    user=settings.DB_USER, password=settings.DB_PASSWORD,
    database=settings.DB_NAME, charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
c = conn.cursor()

print("=" * 80)
print("EXTRA 1: All projects with ProjectWorkflowConfigs")
print("=" * 80)
c.execute("""
    SELECT pwc.project_id, p.code AS project_code, p.name AS project_name,
           COUNT(*) AS config_count
    FROM project_workflow_configs pwc
    LEFT JOIN projects p ON p.id = pwc.project_id
    GROUP BY pwc.project_id
    ORDER BY pwc.project_id
""")
for row in c.fetchall():
    print(f"  project_id={row['project_id']}, code={row['project_code']}, name={row['project_name']}, configs={row['config_count']}")

print()
print("=" * 80)
print("EXTRA 2: Check what project_id=41 and project_id=3 are")
print("=" * 80)
c.execute("SELECT id, code, name FROM projects WHERE id IN (41, 3, 23)")
for row in c.fetchall():
    print(f"  id={row['id']}, code={row['code']}, name={row['name']}")

print()
print("=" * 80)
print("EXTRA 3: Check the indent_69 and 70 - what project are they for?")
print("=" * 80)
c.execute("""
    SELECT i.id, i.indent_number, i.project_id, i.raised_by, i.status, i.created_at,
           p.code AS project_code, p.name AS project_name
    FROM indents i
    LEFT JOIN projects p ON p.id = i.project_id
    WHERE i.id IN (69, 70)
""")
for row in c.fetchall():
    print(f"  Indent: id={row['id']}, number={row['indent_number']}")
    print(f"    project_id={row['project_id']}, project_code={row['project_code']}, project_name={row['project_name']}")
    print(f"    raised_by={row['raised_by']}, status={row['status']}")

print()
print("=" * 80)
print("EXTRA 4: Check full hierarchy from position_id=3049 (Storekeeper) upward")
print("=" * 80)
# Walk up manually
visited = set()
curr_id = 3049
level = 0
while curr_id and curr_id not in visited:
    visited.add(curr_id)
    c.execute("""
        SELECT p.id, p.name, p.code, p.role_id, p.parent_position_id,
               p.role_name,
               r.name AS role_name2, r.code AS role_code
        FROM positions p
        LEFT JOIN roles r ON r.id = p.role_id
        WHERE p.id = %s
    """, (curr_id,))
    pos = c.fetchone()
    if not pos:
        break
    print(f"  Level {level}: id={pos['id']}, name={pos['name']}, code={pos['code']}")
    print(f"           role_id={pos['role_id']}, role_code={pos['role_code']}, role_name={pos['role_name'] or pos['role_name2']}")
    curr_id = pos['parent_position_id']
    level += 1

print()
print("=" * 80)
print("EXTRA 5: Check if there's an OE position related to Storekeeper's chain")
print("=" * 80)
# Find all OE positions
c.execute("""
    SELECT p.id, p.name, p.code, p.parent_position_id, p.project_id,
           r.code AS role_code
    FROM positions p
    JOIN roles r ON r.id = p.role_id
    WHERE r.code IN ('oe', 'operations_executive')
""")
print("  OE positions in the system:")
for row in c.fetchall():
    print(f"    id={row['id']}, name={row['name']}, code={row['code']}, parent={row['parent_position_id']}, project={row['project_id']}")

print()
print("=" * 80)
print("EXTRA 6: What position should be the parent of STOREKEEPER (3049)?")
print("=" * 80)
c.execute("""
    SELECT id, name, code, role_name, role_id, parent_position_id, project_id
    FROM positions
    WHERE id = (SELECT parent_position_id FROM positions WHERE id = 3049)
""")
pos = c.fetchone()
if pos:
    print(f"  Parent of 3049: id={pos['id']}, name={pos['name']}, code={pos['code']}")
    print(f"    role_name={pos['role_name']}, role_id={pos['role_id']}")
else:
    print("  No parent found for position 3049")

print()
print("=" * 80)
print("EXTRA 7: Check what positions have OE as their role")
print("=" * 80)
c.execute("""
    SELECT p.id, p.name, p.code, p.parent_position_id,
           p.project_id, p.role_id,
           r.code AS role_code, r.name AS role_name
    FROM positions p
    JOIN roles r ON r.id = p.role_id
    WHERE LOWER(r.code) = 'oe' OR LOWER(r.name) LIKE '%operation%executive%'
       OR (LOWER(r.name) LIKE '%oe%' AND LOWER(r.name) LIKE '%operation%')
""")
for row in c.fetchall():
    print(f"  id={row['id']}, name={row['name']}, code={row['code']}")
    print(f"    parent={row['parent_position_id']}, project={row['project_id']}")
    print(f"    role_id={row['role_id']}, role_code={row['role_code']}, role_name={row['role_name']}")

print()
print("=" * 80)
print("EXTRA 8: Check the Divisional Manager role/position")
print("=" * 80)
c.execute("""
    SELECT r.id, r.name, r.code FROM roles r
    WHERE LOWER(r.name) LIKE '%division%' OR LOWER(r.code) LIKE '%division%'
       OR LOWER(r.name) LIKE '%divisional%'
""")
for row in c.fetchall():
    print(f"  Role: id={row['id']}, name={row['name']}, code={row['code']}")

c.execute("""
    SELECT p.id, p.name, p.code, p.parent_position_id, p.role_id
    FROM positions p
    WHERE p.id = 5880
""")
pos = c.fetchone()
if pos:
    print(f"  Position 5880: id={pos['id']}, name={pos['name']}, code={pos['code']}")
    print(f"    role_id={pos['role_id']}, parent={pos['parent_position_id']}")

conn.close()
