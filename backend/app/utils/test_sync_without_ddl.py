import asyncio
from app.database import AsyncSessionLocal
from app.utils.schema_sync import ensure_organization_structure_schema

async def test_with_ddl():
    print("Testing lifecycle WITH schema sync DDL...")
    async with AsyncSessionLocal() as session:
        try:
            await ensure_organization_structure_schema(session)
            await session.commit()
            print("With DDL: Success")
        except Exception as e:
            print("With DDL failed:", type(e), str(e))

async def test_without_ddl():
    print("\nTesting lifecycle WITHOUT schema sync DDL...")
    async with AsyncSessionLocal() as session:
        try:
            # Just do a simple query or nothing, and commit
            await session.commit()
            print("Without DDL: Success")
        except Exception as e:
            print("Without DDL failed:", type(e), str(e))

async def main():
    await test_with_ddl()
    await test_without_ddl()

if __name__ == "__main__":
    asyncio.run(main())
