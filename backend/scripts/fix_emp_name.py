"""Fix emp.first_name/emp.last_name to emp.name in logistics.py."""
import re

LOGISTICS_PATH = r"C:\Users\User-4\Downloads\bhspl_release v1.1proc\backend\app\api\v1\logistics.py"

with open(LOGISTICS_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'emp_name = (emp.first_name or "") + " " + (emp.last_name or "")\n                emp_name = emp_name.strip()'
new = 'emp_name = emp.name or ""'

if old in content:
    content = content.replace(old, new, 1)
    with open(LOGISTICS_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Fixed: emp.first_name/last_name -> emp.name")
else:
    print("✗ Pattern not found. Checking current line 788...")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'first_name' in line or 'last_name' in line:
            print(f"  Line {i+1}: {line.strip()}")
    if not any('first_name' in l for l in lines):
        print("  (Pattern already fixed - no first_name references found)")
