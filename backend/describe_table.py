import asyncio
from app.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        # Check current column details
        res = await session.execute(text("DESCRIBE logistics_main_dispatch_orders;"))
        columns = res.all()
        for col in columns:
            if col[0] == 'status':
                print(f"Col status details: Field={col[0]}, Type={col[1]}, Null={col[2]}, Key={col[3]}, Default={col[4]}, Extra={col[5]}")

if __name__ == "__main__":
    asyncio.run(main())
