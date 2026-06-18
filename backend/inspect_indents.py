import asyncio
import os
import sys
import logging

# Suppress all loggers
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.WARNING)
logging.getLogger().setLevel(logging.WARNING)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.indent import Indent
from app.models.user import User
from app.models.settings_master import Employee, Position
from app.models.approval import ApprovalRequest

async def run_inspection():
    out = []
    def log(msg):
        out.append(msg)
        print(msg)

    async with AsyncSessionLocal() as db:
        q = select(Indent).order_by(Indent.id.desc()).limit(30)
        res = await db.execute(q)
        indents = res.scalars().all()
        log(f"Total Indents found: {len(indents)}")
        for ind in indents:
            user = await db.get(User, ind.raised_by)
            emp = await db.get(Employee, user.employee_id) if user and user.employee_id else None
            pos = await db.get(Position, emp.position_id) if emp and emp.position_id else None
            log(f"\nIndent ID: {ind.id}, Indent No: {ind.indent_number}, Status: {ind.status}")
            log(f"  Raised by User: ID={ind.raised_by}, Username={user.username if user else 'N/A'}, EmpName={emp.name if emp else 'N/A'}, PosName={pos.name if pos else 'N/A'}, PosID={pos.id if pos else 'N/A'}")
            
            # Check if there is an ApprovalRequest
            q_req = select(ApprovalRequest).where(
                ApprovalRequest.document_type == "indent",
                ApprovalRequest.document_id == ind.id
            )
            res_req = await db.execute(q_req)
            req = res_req.scalar_one_or_none()
            if req:
                log(f"  Approval Request ID: {req.id}, Status: {req.status}, Current Level: {req.current_level}, Total Levels: {req.total_levels}")
                # check active position
                from app.services.approval_service import get_hierarchical_active_position
                active_pos = await get_hierarchical_active_position(db, req, req.current_level)
                if active_pos:
                    log(f"    Current Active Approval Position: ID={active_pos.id}, Name={active_pos.name}, Code={active_pos.code}, RoleID={active_pos.role_id}")
                else:
                    log("    No Active Approval Position found for current level!")
            else:
                log("  No Approval Request found for this indent!")

    # Write output to file in UTF-8
    with open("inspect_indents_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Inspection complete. Saved to inspect_indents_result.txt")

asyncio.run(run_inspection())
