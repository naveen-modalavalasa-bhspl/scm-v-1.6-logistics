import subprocess
import time
import httpx
import asyncio

async def main():
    # Start uvicorn server on port 8005
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "app.main:app", "--port", "8005"],
        cwd="C:\\Users\\User-4\\Desktop\\scm\\bhspl_release v1.5 logistics\\backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    # Wait for server to start
    await asyncio.sleep(10)
    
    # Get database connection & generate token
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from app.api.v1.auth import create_access_token
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).where(User.is_active == True).limit(1))
        user = user_res.scalar_one_or_none()
        token = create_access_token(data={"sub": user.username})
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("Sending request to port 8005...")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "http://localhost:8005/api/v1/users/employees/sync-api",
                json=None,
                headers=headers
            )
            print("Status:", res.status_code)
            print("Response:", res.text)
    except Exception as e:
        print("HTTP request failed:", e)
        
    # Terminate server and read all output
    proc.terminate()
    stdout, _ = proc.communicate(timeout=5)
    print("--- SERVER LOGS ---")
    print(stdout)

if __name__ == "__main__":
    asyncio.run(main())
