import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.approval import ApprovalRequest, ApprovalHistory
from app.models.user import User

async def run():
    async with AsyncSessionLocal() as db:
        req_id = 204
        req = await db.get(ApprovalRequest, req_id)
        if req:
            print(f"Approval Request {req_id}: Status={req.status}, Current Level={req.current_level}, Total Levels={req.total_levels}")
            q_hist = select(ApprovalHistory).where(ApprovalHistory.request_id == req_id).order_by(ApprovalHistory.id.asc())
            res_hist = await db.execute(q_hist)
            hist = res_hist.scalars().all()
            print(f"History entries: {len(hist)}")
            for h in hist:
                u = await db.get(User, h.action_by)
                print(f"  Level {h.level}: Action={h.action}, ActionBy={u.username if u else 'N/A'} (ID={h.action_by}), Comments={h.comments}, Timestamp={h.action_date}")
        else:
            print(f"Request {req_id} not found")

asyncio.run(run())
