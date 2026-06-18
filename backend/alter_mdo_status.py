import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        try:
            print("Altering logistics_main_dispatch_orders.status to VARCHAR(50)...")
            await session.execute(
                text("ALTER TABLE logistics_main_dispatch_orders MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'DRAFT';")
            )
            await session.commit()
            print("Successfully altered column status to VARCHAR(50)!")
        except Exception as e:
            print("Error altering table:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
