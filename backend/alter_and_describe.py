import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        try:
            print("Before alter:")
            res = await session.execute(text("DESCRIBE logistics_main_dispatch_orders;"))
            for col in res.all():
                if col[0] == 'status':
                    print(f"Col status: Type={col[1]}")

            print("Running ALTER TABLE...")
            # Let's try with CHANGE COLUMN or just MODIFY COLUMN
            await session.execute(
                text("ALTER TABLE logistics_main_dispatch_orders MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'DRAFT';")
            )
            await session.commit()
            print("Altered. Re-describing:")
            
            res2 = await session.execute(text("DESCRIBE logistics_main_dispatch_orders;"))
            for col in res2.all():
                if col[0] == 'status':
                    print(f"Col status after: Type={col[1]}")
        except Exception as e:
            print("Error:")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
