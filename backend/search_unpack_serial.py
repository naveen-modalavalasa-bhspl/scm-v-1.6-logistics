"""Search for SerialNumber updates/inserts in warehouse.py."""
with open("c:/Users/User-4/Desktop/scm/bhspl_release v1.5 logistics/backend/app/api/v1/warehouse.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "SerialNumber" in line or "serial" in line:
            if "select" not in line.lower() or "update" in line.lower() or "add" in line.lower() or "=" in line:
                if len(line.strip()) < 120:
                    print(f"L{i}: {line.strip()}")
