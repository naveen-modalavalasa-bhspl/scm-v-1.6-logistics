"""Diagnose why indents are not showing for the OE approver.

Run: python indent_diag.py
"""
import sys
sys.path.insert(0, '.')
import pymysql
from app.config import settings

conn = pymysql.connect(
    host=settings.DB_HOST,
    port=settings.DB_PORT,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
c = conn.cursor()

print("=" * 80)
print("DIAG 1: Check the indent raisers (user_id=59 and user_id=7)")
print("=" * 80)
c.execute("""
    SELECT u.id, u.username, u.employee_code, u.employee_id,
           u.active_role_id, ua.role_id AS any_role_id,
           r.name AS role_name, r.code AS role_code
    FROM users u
    LEFT JOIN user_roles ua ON ua.user_id = u.id
    LEFT JOIN roles r ON r.id = ua.role_id
    WHERE u.id IN (59, 7)
    ORDER BY u.id, r.code
""")
for row in c.fetchall():
    print(f"  User: id={row['id']}, username={row['username']}, emp_code={row['employee_code']}")
    print(f"    employee_id={row['employee_id']}, active_role_id={row['active_role_id']}")
    print(f"    role: id={row['any_role_id']}, name={row['role_name']}, code={row['role_code']}")

print()
print("=" * 80)
print("DIAG 2: Employees of the indent raisers")
print("=" * 80)
c.execute("""
    SELECT e.id, e.employee_code, e.name,
           e.position_id, p.name AS position_name, p.code AS position_code,
           p.role_id, p.parent_position_id,
           r.name AS role_name, r.code AS role_code
    FROM employees e
    JOIN users u ON u.employee_id = e.id
    LEFT JOIN positions p ON p.id = e.position_id
    LEFT JOIN roles r ON r.id = p.role_id
    WHERE u.id IN (59, 7)
""")
for row in c.fetchall():
    print(f"  Employee: id={row['id']}, code={row['employee_code']}, name={row['name']}")
    print(f"    position_id={row['position_id']}, position_name={row['position_name']}")
    print(f"    position_code={row['position_code']}, role_id={row['role_id']}")
    print(f"    role_name={row['role_name']}, role_code={row['role_code']}")
    print(f"    parent_position_id={row['parent_position_id']}")

print()
print("=" * 80)
print("DIAG 3: Position hierarchy from user_id=59's position upward Step 1 - direct position")
print("=" * 80)
c.execute("""
    SELECT e.position_id FROM employees e
    JOIN users u ON u.employee_id = e.id
    WHERE u.id = 59
""")
emp_row = c.fetchone()
if emp_row and emp_row['position_id']:
    start_pos_id = emp_row['position_id']
    visited = set()
    curr_id = start_pos_id
    level = 0
    print(f"  Starting from position_id={start_pos_id}")
    while curr_id and curr_id not in visited:
        visited.add(curr_id)
        c.execute("""
            SELECT p.id, p.name, p.code, p.role_id, p.parent_position_id,
                   p.project_id, p.employee_id,
                   r.name AS role_name, r.code AS role_code
            FROM positions p
            LEFT JOIN roles r ON r.id = p.role_id
            WHERE p.id = %s
        """, (curr_id,))
        pos = c.fetchone()
        if not pos:
            break
        indent = "  " * (level + 1)
        print(f"  {indent}Level {level}: id={pos['id']}, name={pos['name']}, code={pos['code']}")
        print(f"  {indent}  role_id={pos['role_id']}, role_name={pos['role_name']}, role_code={pos['role_code']}")
        print(f"  {indent}  project_id={pos['project_id']}, employee_id={pos['employee_id']}")
        print(f"  {indent}  parent_position_id={pos['parent_position_id']}")
        curr_id = pos['parent_position_id']
        level += 1
else:
    print("  No position found for user_id=59")

print()
print("=" * 80)
print("DIAG 3b: Position hierarchy from user_id=7's position upward")
print("=" * 80)
c.execute("""
    SELECT e.position_id FROM employees e
    JOIN users u ON u.employee_id = e.id
    WHERE u.id = 7
""")
emp_row = c.fetchone()
if emp_row and emp_row['position_id']:
    start_pos_id = emp_row['position_id']
    visited = set()
    curr_id = start_pos_id
    level = 0
    print(f"  Starting from position_id={start_pos_id}")
    while curr_id and curr_id not in visited:
        visited.add(curr_id)
        c.execute("""
            SELECT p.id, p.name, p.code, p.role_id, p.parent_position_id,
                   p.project_id, p.employee_id,
                   r.name AS role_name, r.code AS role_code
            FROM positions p
            LEFT JOIN roles r ON r.id = p.role_id
            WHERE p.id = %s
        """, (curr_id,))
        pos = c.fetchone()
        if not pos:
            break
        indent = "  " * (level + 1)
        print(f"  {indent}Level {level}: id={pos['id']}, name={pos['name']}, code={pos['code']}")
        print(f"  {indent}  role_id={pos['role_id']}, role_name={pos['role_name']}, role_code={pos['role_code']}")
        print(f"  {indent}  project_id={pos['project_id']}, employee_id={pos['employee_id']}")
        print(f"  {indent}  parent_position_id={pos['parent_position_id']}")
        curr_id = pos['parent_position_id']
        level += 1
else:
    print("  No position found for user_id=7")

print()
print("=" * 80)
print("DIAG 4: HR-EMP-07298 (OE/DM user) - check employee & position mapping")
print("=" * 80)
c.execute("""
    SELECT u.id, u.username, u.employee_code, u.employee_id,
           u.active_role_id,
           e.id AS emp_id, e.employee_code AS emp_code,
           e.name AS emp_name, e.position_id AS emp_position_id,
           pos.id AS position_id, pos.name AS position_name,
           pos.code AS position_code, pos.role_id AS position_role_id,
           pos.employee_id AS pos_employee_id,
           r.id AS role_id, r.name AS role_name, r.code AS role_code
    FROM users u
    LEFT JOIN employees e ON e.id = u.employee_id
    LEFT JOIN positions pos ON (pos.id = e.position_id OR pos.employee_id = u.employee_id)
    LEFT JOIN roles r ON r.id = pos.role_id
    WHERE u.employee_code = 'HR-EMP-07298'
       OR u.username LIKE '%07298%'
""")
for row in c.fetchall():
    print(f"  User: id={row['id']}, username={row['username']}, emp_code={row['employee_code']}")
    print(f"    employee_id={row['employee_id']}, active_role_id={row['active_role_id']}")
    print(f"    Employee: id={row['emp_id']}, code={row['emp_code']}, name={row['emp_name']}")
    print(f"    emp.position_id={row['emp_position_id']}")
    print(f"    Position: id={row['position_id']}, name={row['position_name']}")
    print(f"    position.employee_id={row['pos_employee_id']}")
    print(f"    position_role_id={row['position_role_id']}")
    print(f"    Role: id={row['role_id']}, name={row['role_name']}, code={row['role_code']}")

print()
print("=" * 80)
print("DIAG 5: Find OE and DM positions/roles")
print("=" * 80)
c.execute("""
    SELECT id, name, code FROM roles
    WHERE LOWER(name) LIKE '%oe%' OR LOWER(name) LIKE '%executive%'
       OR LOWER(name) LIKE '%district%' OR LOWER(name) LIKE '%operation%'
       OR LOWER(code) LIKE '%oe%' OR LOWER(code) LIKE '%dm%'
    ORDER BY name
""")
for row in c.fetchall():
    print(f"  Role: id={row['id']}, name={row['name']}, code={row['code']}")

print()
print("=" * 80)
print("DIAG 6: Positions with these role ids")
print("=" * 80)
c.execute("""
    SELECT p.id, p.name, p.code, p.role_id, p.employee_id,
           p.parent_position_id, p.project_id,
           r.name AS role_name, r.code AS role_code,
           e.name AS emp_name, e.employee_code
    FROM positions p
    LEFT JOIN roles r ON r.id = p.role_id
    LEFT JOIN employees e ON e.id = p.employee_id
    WHERE r.code IN ('oe', 'operations_executive', 'dm', 'district_manager')
       OR LOWER(r.name) LIKE '%oe%' OR LOWER(r.name) LIKE '%executive%'
       OR LOWER(r.name) LIKE '%district%'
    ORDER BY r.name, p.name
""")
for row in c.fetchall():
    print(f"  Position: id={row['id']}, name={row['name']}, code={row['code']}")
    print(f"    role_id={row['role_id']}, role_name={row['role_name']}, role_code={row['role_code']}")
    print(f"    employee_id={row['employee_id']}, emp={row['emp_name']}/{row['employee_code']}")
    print(f"    parent_position_id={row['parent_position_id']}, project_id={row['project_id']}")

print()
print("=" * 80)
print("DIAG 7: ProjectWorkflowConfig for project_id=41")
print("=" * 80)
c.execute("""
    SELECT pwc.*, r.name AS role_name, r.code AS role_code
    FROM project_workflow_configs pwc
    JOIN roles r ON r.id = pwc.role_id
    WHERE pwc.project_id = 41
    ORDER BY r.name
""")
for row in c.fetchall():
    print(f"  id={row['id']}, role_id={row['role_id']}, role_name={row['role_name']}, code={row['role_code']}")
    print(f"    indent_approve={row['indent_approve']}, indent_view={row['indent_view']}")
    print(f"    dispatch_approve={row['dispatch_approve']}, dispatch_view={row['dispatch_view']}")

if c.rowcount == 0:
    print("  NO CONFIG FOUND FOR PROJECT 41!")

print()
print("=" * 80)
print("DIAG 8: ProjectWorkflowConfig for project_id=3")
print("=" * 80)
c.execute("""
    SELECT pwc.*, r.name AS role_name, r.code AS role_code
    FROM project_workflow_configs pwc
    JOIN roles r ON r.id = pwc.role_id
    WHERE pwc.project_id = 3
    ORDER BY r.name
""")
for row in c.fetchall():
    print(f"  id={row['id']}, role_id={row['role_id']}, role_name={row['role_name']}, code={row['role_code']}")
    print(f"    indent_approve={row['indent_approve']}, indent_view={row['indent_view']}")

if c.rowcount == 0:
    print("  NO CONFIG FOUND FOR PROJECT 3!")

print()
print("=" * 80)
print("DIAG 9: Approval requests for indents 68, 69, 70")
print("=" * 80)
c.execute("""
    SELECT ar.*, aw.name AS workflow_name, aw.project_id AS wf_project_id
    FROM approval_requests ar
    LEFT JOIN approval_workflows aw ON aw.id = ar.workflow_id
    WHERE ar.document_id IN (68, 69, 70) AND ar.document_type = 'indent'
    ORDER BY ar.id
""")
for row in c.fetchall():
    print(f"  Request: id={row['id']}, doc_id={row['document_id']}, doc_number={row['document_number']}")
    print(f"    status={row['status']}, cur_level={row['current_level']}, total_levels={row['total_levels']}")
    print(f"    workflow_id={row['workflow_id']}, wf_name={row['workflow_name']}, wf_project_id={row['wf_project_id']}")

if c.rowcount == 0:
    print("  NO APPROVAL REQUESTS FOUND FOR THESE INDENTS!")
    
    # Check if they even called submit_for_approval
    print()
    print("  >>> No approval requests means submit_for_approval() was never called!")
    print("  >>> Check the indent lifecycle code to see when submit is triggered.")

print()
print("=" * 80)
print("DIAG 10: User warehouses for indent raisers")
print("=" * 80)
c.execute("""
    SELECT uw.user_id, uw.warehouse_id, uw.role_id,
           w.name AS warehouse_name,
           r.code AS role_code
    FROM user_warehouses uw
    LEFT JOIN warehouses w ON w.id = uw.warehouse_id
    LEFT JOIN roles r ON r.id = uw.role_id
    WHERE uw.user_id IN (59, 7)
""")
for row in c.fetchall():
    print(f"  user_id={row['user_id']}, warehouse={row['warehouse_name']}, role_id={row['role_id']}, role_code={row['role_code']}")

print()
print("=" * 80)
print("DIAG 11: Find HR-EMP-07298 user details")
print("=" * 80)
c.execute("""
    SELECT u.* FROM users u WHERE u.employee_code = 'HR-EMP-07298'
       OR u.username LIKE '%07298%'
""")
for row in c.fetchall():
    print(f"  User: id={row['id']}, username={row['username']}, emp_code={row['employee_code']}")
    print(f"    employee_id={row['employee_id']}, active_role_id={row['active_role_id']}")

print()
print("=" * 80)
print("DIAG 12: User warehouses for HR-EMP-07298")
print("=" * 80)
c.execute("""
    SELECT uw.*, w.name AS warehouse_name, r.code AS role_code, r.name AS role_name
    FROM user_warehouses uw
    LEFT JOIN warehouses w ON w.id = uw.warehouse_id
    LEFT JOIN roles r ON r.id = uw.role_id
    WHERE uw.user_id = (SELECT id FROM users WHERE employee_code = 'HR-EMP-07298' LIMIT 1)
""")
for row in c.fetchall():
    print(f"  warehouse_id={row['warehouse_id']}, warehouse={row['warehouse_name']}, role_id={row['role_id']}, role_code={row['role_code']}")

if c.rowcount == 0:
    print("  NO USER_WAREHOUSE RECORDS FOR HR-EMP-07298")

conn.close()
