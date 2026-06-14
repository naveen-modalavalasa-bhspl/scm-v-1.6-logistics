import re

filepath = r"c:\Users\User-4\Downloads\bhspl_release v1.1proc\backend\app\api\v1\procurement.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

pattern = re.compile(r'@router\.(get|post|put|delete|patch|options|head)\("([^"]*)"')

for idx, line in enumerate(lines):
    match = pattern.search(line)
    if match:
        route_path = match.group(2)
        # Find any {...} that do not contain a colon ':'
        placeholders = re.findall(r'\{([^}:]+)\}', route_path)
        if placeholders:
            print(f"{idx+1}: {line.strip()} -> placeholders without type: {placeholders}")
