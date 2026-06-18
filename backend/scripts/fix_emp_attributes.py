"""Fix Employee attribute errors in logistics.py:
1. emp.first_name/last_name -> emp.name
2. emp.code -> emp.employee_code
"""
LOGISTICS_PATH = r"C:\Users\User-4\Downloads\bhspl_release v1.1proc\backend\app\api\v1\logistics.py"

with open(LOGISTICS_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# Fix 1: emp.first_name/last_name -> emp.name
old1 = 'emp_name = (emp.first_name or "") + " " + (emp.last_name or "")\n                emp_name = emp_name.strip()'
new1 = 'emp_name = emp.name or ""'
if old1 in content:
    content = content.replace(old1, new1, 1)
    changes += 1
    print("✓ Fixed: first_name/last_name -> name")
else:
    print("✗ Fix 1: Pattern not found (may already be fixed)")

# Fix 2: emp.code or emp.employee_code -> emp.employee_code
old2 = 'emp_code = emp.code or emp.employee_code'
new2 = 'emp_code = emp.employee_code'
if old2 in content:
    content = content.replace(old2, new2, 1)
    changes += 1
    print("✓ Fixed: emp.code -> emp.employee_code")
else:
    print("✗ Fix 2: Pattern not found (may already be fixed)")

if changes > 0:
    with open(LOGISTICS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✓ {changes} change(s) applied")
else:
    print("\n✗ No changes made")
