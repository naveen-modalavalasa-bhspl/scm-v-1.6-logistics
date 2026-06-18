"""Check project 23's configs and trace exact approval chain."""
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
print("CHECK 1: ProjectWorkflowConfig for project_id=23 (AP-104-MOBILE-MEDICAL-UNIT)")
print("=" * 80)
c.execute("""
    SELECT pwc.*, r.name AS role_name, r.code AS role_code
    FROM project_workflow_configs pwc
    JOIN roles r ON r.id = pwc.role_id
    WHERE pwc.project_id = 23
    ORDER BY r.name
""")
print(f"  Found {c.rowcount} configs:")
for row in c.fetchall():
    print(f"  id={row['id']}, role_id={row['role_id']}, role_name={row['role_name']}, code={row['role_code']}")
    print(f"    indent_approve={row['indent_approve']}, indent_view={row['indent_view']}")

print()
print("=" * 80)
print("CHECK 2: What role_ids do the Storekeeper's ancestors have?")
print("=" * 80)
for pos_id in [3049, 5880, 137, 5929]:
    c.execute("""
        SELECT p.id, p.name, p.code, p.role_id, r.name AS role_name, r.code AS role_code
        FROM positions p
        LEFT JOIN roles r ON r.id = p.role_id
        WHERE p.id = %s
    """, (pos_id,))
    pos = c.fetchone()
    if pos:
        print(f"  Position {pos_id}: name={pos['name']}, role_id={pos['role_id']}, role_code={pos['role_code']}, role_name={pos['role_name']}")

print()
print("=" * 80)
print("CHECK 3: Match ancestors' role_ids against project 23 configs")
print("=" * 80)
c.execute("""
    SELECT p.id AS position_id, p.name AS position_name, p.role_id,
           r.code AS role_code,
           pwc.id AS config_id, pwc.indent_approve, pwc.indent_view
    FROM positions p
    LEFT JOIN roles r ON r.id = p.role_id
    LEFT JOIN project_workflow_configs pwc 
        ON pwc.role_id = p.role_id AND pwc.project_id = 23
    WHERE p.id IN (3049, 5880, 137, 5929)
    ORDER BY FIELD(p.id, 3049, 5880, 137, 5929)
""")
for row in c.fetchall():
    print(f"  Position {row['position_id']} ({row['position_name']})")
    print(f"    role_id={row['role_id']}, role_code={row['role_code']}")
    if row['config_id']:
        print(f"    CONFIG FOUND: indent_approve={row['indent_approve']}, indent_view={row['indent_view']}")
    else:
        print(f"    NO CONFIG FOUND for project 23!")
        # Check if config exists for ANY project
        c.execute("""
            SELECT project_id, indent_approve, indent_view
            FROM project_workflow_configs WHERE role_id = %s
        """, (row['role_id'],))
        other_configs = c.fetchall()
        if other_configs:
            print(f"    Config exists for OTHER projects:")
            for oc in other_configs:
                print(f"      project_id={oc['project_id']}: approve={oc['indent_approve']}, view={oc['indent_view']}")
        else:
            print(f"    No config for this role in ANY project")

print()
print("=" * 80)
print("CHECK 4: Approval request details for indent 69")
print("=" * 80)
c.execute("""
    SELECT ar.*, aw.name AS workflow_name, aw.project_id AS wf_project_id
    FROM approval_requests ar
    LEFT JOIN approval_workflows aw ON aw.id = ar.workflow_id
    WHERE ar.document_id = 69 AND ar.document_type = 'indent'
""")
row = c.fetchone()
if row:
    print(f"  Request id={row['id']}, status={row['status']}")
    print(f"  current_level={row['current_level']}, total_levels={row['total_levels']}")
    print(f"  workflow_id={row['workflow_id']}, wf_name={row['workflow_name']}")
    print(f"  wf_project_id={row['wf_project_id']}")
    print(f"  requested_by={row['requested_by']}")
    # Check approval history
    c.execute("SELECT * FROM approval_histories WHERE request_id = %s ORDER BY id", (row['id'],))
    print(f"  History entries: {c.rowcount}")
    for h in c.fetchall():
        print(f"    action={h['action']}, action_by={h['action_by']}, level={h['level']}")

print()
print("=" * 80)
print("CHECK 5: Does the position hierarchy connect to any OE position?")
print("=" * 80)
# Check if any OE position has a child that's in the chain or is a parent of any chain element
c.execute("""
    SELECT p.id, p.name, p.code, p.parent_position_id, p.role_id,
           r.code AS role_code
    FROM positions p
    JOIN roles r ON r.id = p.role_id
    WHERE LOWER(r.code) = 'oe'
""")
oe_positions = c.fetchall()
print(f"  Found {len(oe_positions)} OE positions")
for op in oe_positions[:10]:  # show first 10
    print(f"    id={op['id']}, name={op['name']}, parent={op['parent_position_id']}")

# Check if OE position 5930 is the parent of RM (137)
c.execute("SELECT parent_position_id FROM positions WHERE id = 137")
rm_parent = c.fetchone()
print(f"\n  Regional Manager (137) parent_id = {rm_parent['parent_position_id'] if rm_parent else 'N/A'}")

c.execute("SELECT parent_position_id FROM positions WHERE id = 5929")
sph_parent = c.fetchone()
print(f"  SPH (5929) parent_id = {sph_parent['parent_position_id'] if sph_parent else 'N/A'}")

# Check if Div Manager (5880) is somehow connected to OE
c.execute("SELECT parent_position_id FROM positions WHERE id = 5880")
dm_parent = c.fetchone()
print(f"  Div Manager (5880) parent_id = {dm_parent['parent_position_id'] if dm_parent else 'N/A'}")
print(f"  This goes to position 137 (Regional Manager)")
print(f"  Chain: Storekeeper(3049) -> DivManager(5880) -> RegionalMgr(137) -> SPH(5929)")

print()
print("=" * 80)
print("CHECK 6: Warehouse check - what warehouse is 41?")
print("=" * 80)
c.execute("SELECT id, code, name FROM warehouses WHERE id = 41")
w = c.fetchone()
print(f"  Warehouse 41: {w}")

# Check user_warehouses for the OE user
c.execute("""
    SELECT u.id, u.username, u.employee_code, u.active_role_id
    FROM users u WHERE u.employee_code = 'HR-EMP-07298'
       OR u.username LIKE '%07298%'
""")
u = c.fetchone()
if u:
    print(f"\n  OE User: id={u['id']}, username={u['username']}, active_role_id={u['active_role_id']}")
    c.execute("SELECT * FROM user_warehouses WHERE user_id = %s", (u['id'],))
    print(f"  Warehouses:")
    for uw in c.fetchall():
        print(f"    warehouse_id={uw['warehouse_id']}, role_id={uw['role_id']}")

print()
print("=" * 80)
print("CHECK 7: What position does the OE user occupy?")
print("=" * 80)
if u:
    c.execute("""
        SELECT e.id, e.employee_code, e.name, e.position_id,
               p.name AS pos_name, p.code AS pos_code, p.role_id,
               r.code AS role_code, r.name AS role_name
        FROM employees e
        JOIN users u ON u.employee_id = e.id
        LEFT JOIN positions p ON p.id = e.position_id
        LEFT JOIN roles r ON r.id = p.role_id
        WHERE u.id = %s
    """, (u['id'],))
    for emp in c.fetchall():
        print(f"  Employee: id={emp['id']}, code={emp['employee_code']}, name={emp['name']}")
        print(f"    position_id={emp['position_id']}, pos_name={emp['pos_name']}")
        print(f"    role_id={emp['role_id']}, role_code={emp['role_code']}")

conn.close()
