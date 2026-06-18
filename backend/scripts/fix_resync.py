"""Fix the resync_org_structure.py - replace truncate with DROP+CREATE."""
import re

with open('backend/scripts/resync_org_structure.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = '''async def truncate_tables():
    """Truncate tables in FK-safe order (children first)."""
    print("[1/5] Truncating tables...")
    async with engine.connect() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in ("positions", "employees", "offices", "projects"):
            await conn.execute(text(f"DELETE FROM `{table}`"))
            print(f"  Truncated {table}")
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        await conn.commit()'''

new_func = '''async def drop_and_recreate_tables():
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

    # Re-create via SQLAlchemy metadata
    async with engine.begin() as conn:
        await conn.run_sync(Project.__table__.create)
        await conn.run_sync(Office.__table__.create)
        await conn.run_sync(Position.__table__.create)
        await conn.run_sync(Employee.__table__.create)
        print("  Recreated all tables with current model schema")'''

count = content.count(old_func)
print(f"Found {count} occurrences of old function")

if count > 0:
    content = content.replace(old_func, new_func, 1)
    # Also update the call site
    content = content.replace("await truncate_tables()", "await drop_and_recreate_tables()")
    
    with open('backend/scripts/resync_org_structure.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replacement done successfully")
else:
    print("Old function not found - checking current state")
    if "drop_and_recreate_tables" in content:
        print("File already has the new function")
    elif "DELETE FROM" in content:
        print("Still has old code but function name might differ")
    # Print what's there
    for line in content.split('\n'):
        if 'truncate' in line.lower() or 'drop' in line.lower() or 'DELETE' in line:
            print(f"  LINE: {line.strip()[:100]}")
