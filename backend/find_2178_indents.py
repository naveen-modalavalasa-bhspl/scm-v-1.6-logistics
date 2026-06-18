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
from app.models.settings_master import Position, Employee
from app.models.user import User
from app.models.indent import Indent
from app.models.approval import ApprovalRequest

async def run():
    out = []
    def log(msg):
        out.append(msg)
        print(msg)

    async with AsyncSessionLocal() as db:
        p2178 = await db.get(Position, 2178)
        p2131 = await db.get(Position, 2131)
        
        log(f"Position 2178: Project ID={p2178.project_id if p2178 else 'N/A'}")
        log(f"Position 2131: Project ID={p2131.project_id if p2131 else 'N/A'}")
        
        if p2178 and p2178.employee_id:
            emp = await db.get(Employee, p2178.employee_id)
            if emp:
                log(f"Employee linked to Position 2178: ID={emp.id}, Code={emp.employee_code}, Name={emp.name}, Position_id={emp.position_id}")
                q_user = select(User).where(User.employee_id == emp.id)
                res_user = await db.execute(q_user)
                users = res_user.scalars().all()
                for u in users:
                    log(f"  User: ID={u.id}, Username={u.username}, active_role_id={u.active_role_id}")
                    q_ind = select(Indent).where(Indent.raised_by == u.id)
                    res_ind = await db.execute(q_ind)
                    indents = res_ind.scalars().all()
                    log(f"  Found {len(indents)} indents raised by this user:")
                    for ind in indents:
                        log(f"    Indent ID: {ind.id}, Indent No: {ind.indent_number}, Status: {ind.status}, ProjectID: {ind.project_id}")
                        q_req = select(ApprovalRequest).where(
                            ApprovalRequest.document_type == "indent",
                            ApprovalRequest.document_id == ind.id
                        )
                        res_req = await db.execute(q_req)
                        req = res_req.scalar_one_or_none()
                        if req:
                            log(f"      Approval Request: ID={req.id}, Status={req.status}, Current Level={req.current_level}, Total Levels={req.total_levels}")
                            from app.services.approval_service import get_level_eligible_approver_ids
                            approvers = await get_level_eligible_approver_ids(db, req.workflow_id, req.current_level)
                            log(f"      Eligible Approver IDs at Level {req.current_level}: {list(approvers)}")
                            log(f"      Is User 60 (OE/DM) in eligible list? {60 in approvers}")
                            
                            from app.services.approval_service import get_hierarchical_active_position
                            act_pos = await get_hierarchical_active_position(db, req, req.current_level)
                            if act_pos:
                                log(f"      Current Active Approval Position: ID={act_pos.id}, Name={act_pos.name}, ProjectID={act_pos.project_id}, RoleID={act_pos.role_id}")
                            else:
                                log("      Current Active Approval Position: None")
                        else:
                            log("      No Approval Request found!")

    with open("find_result_clean.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Inspection complete. Saved to find_result_clean.txt")

asyncio.run(run())
