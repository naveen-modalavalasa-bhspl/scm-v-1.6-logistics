import asyncio
import os
import sys
import logging

# Set sqlalchemy logging to WARNING to keep the output clean
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from sqlalchemy import select, or_
from app.models.settings_master import Position, Employee
from app.models.user import User, UserRole, Role
from app.models.approval import ApprovalRequest, ApprovalWorkflow, ProjectWorkflowConfig
from app.models.indent import Indent
from app.services.approval_service import get_position_ancestors, can_user_approve

async def run_inspection():
    async with AsyncSessionLocal() as db:
        print("=== POSITION 2178 ===")
        p2178 = await db.get(Position, 2178)
        if p2178:
            print(f"ID: {p2178.id}")
            print(f"Name: {p2178.name}")
            print(f"Code: {p2178.code}")
            print(f"Role ID: {p2178.role_id}")
            print(f"Project ID: {p2178.project_id}")
            print(f"Parent Position ID: {p2178.parent_position_id}")
            print(f"Employee ID: {p2178.employee_id}")
        else:
            print("Position 2178 not found!")

        print("\n=== POSITION 2131 ===")
        p2131 = await db.get(Position, 2131)
        if p2131:
            print(f"ID: {p2131.id}")
            print(f"Name: {p2131.name}")
            print(f"Code: {p2131.code}")
            print(f"Role ID: {p2131.role_id}")
            print(f"Project ID: {p2131.project_id}")
            print(f"Parent Position ID: {p2131.parent_position_id}")
            print(f"Employee ID: {p2131.employee_id}")
        else:
            print("Position 2131 not found!")

        print("\n=== ANCESTORS OF 2178 ===")
        ancestors = await get_position_ancestors(db, 2178)
        for idx, a in enumerate(ancestors):
            print(f"{idx+1}. ID: {a.id}, Name: {a.name}, Code: {a.code}, ParentID: {a.parent_position_id}, RoleID: {a.role_id}, ProjectID: {a.project_id}")

        print("\n=== USERS ASSIGNED TO POSITION 2131 ===")
        q_user = select(User).join(Employee, Employee.id == User.employee_id).where(
            or_(
                Employee.position_id == 2131,
                User.employee_id == (p2131.employee_id if p2131 and p2131.employee_id else -1)
            )
        )
        res_user = await db.execute(q_user)
        users_2131 = res_user.scalars().all()
        for u in users_2131:
            emp = await db.get(Employee, u.employee_id)
            print(f"User ID: {u.id}, Username: {u.username}, Active Role ID: {u.active_role_id}, Employee ID: {u.employee_id}, Employee Position ID: {emp.position_id if emp else None}")
            q_roles = select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == u.id)
            res_roles = await db.execute(q_roles)
            roles = res_roles.scalars().all()
            print(f"  Roles: {[r.code for r in roles]}")

        print("\n=== USERS ASSIGNED TO POSITION 2178 ===")
        q_user_2178 = select(User).join(Employee, Employee.id == User.employee_id).where(
            or_(
                Employee.position_id == 2178,
                User.employee_id == (p2178.employee_id if p2178 and p2178.employee_id else -1)
            )
        )
        res_user_2178 = await db.execute(q_user_2178)
        users_2178 = res_user_2178.scalars().all()
        for u in users_2178:
            emp = await db.get(Employee, u.employee_id)
            print(f"User ID: {u.id}, Username: {u.username}, Active Role ID: {u.active_role_id}, Employee ID: {u.employee_id}, Employee Position ID: {emp.position_id if emp else None}")

        print("\n=== INDENTS RAISED BY USERS OF 2178 ===")
        if users_2178:
            user_ids = [u.id for u in users_2178]
            q_ind = select(Indent).where(Indent.raised_by.in_(user_ids))
            res_ind = await db.execute(q_ind)
            indents = res_ind.scalars().all()
            for ind in indents:
                print(f"Indent ID: {ind.id}, Indent No: {ind.indent_number}, Status: {ind.status}, ProjectID: {ind.project_id}")
                q_req = select(ApprovalRequest).where(
                    ApprovalRequest.document_type == "indent",
                    ApprovalRequest.document_id == ind.id
                )
                res_req = await db.execute(q_req)
                req = res_req.scalar_one_or_none()
                if req:
                    print(f"  Approval Request: ID={req.id}, Status={req.status}, Current Level={req.current_level}, Total Levels={req.total_levels}, WorkflowID={req.workflow_id}")
                    for u_2131 in users_2131:
                        can_app = await can_user_approve(db, req.id, u_2131.id)
                        print(f"    Can User {u_2131.username} (ID={u_2131.id}) Approve? {can_app}")
                else:
                    print("  No Approval Request found for this indent!")
        else:
            print("No users found for position 2178, checking directly via Indent.raised_by by employee or code...")
            # Let's see if any indents were raised by employees of position 2178
            q_emp_2178 = select(Employee).where(Employee.position_id == 2178)
            res_emp_2178 = await db.execute(q_emp_2178)
            emps_2178 = res_emp_2178.scalars().all()
            emp_ids = [e.id for e in emps_2178]
            if emp_ids:
                q_user_by_emp = select(User).where(User.employee_id.in_(emp_ids))
                res_user_by_emp = await db.execute(q_user_by_emp)
                users_by_emp = res_user_by_emp.scalars().all()
                user_ids = [u.id for u in users_by_emp]
                if user_ids:
                    q_ind = select(Indent).where(Indent.raised_by.in_(user_ids))
                    res_ind = await db.execute(q_ind)
                    indents = res_ind.scalars().all()
                    for ind in indents:
                        print(f"Indent ID: {ind.id}, Indent No: {ind.indent_number}, Status: {ind.status}, ProjectID: {ind.project_id}")
                        q_req = select(ApprovalRequest).where(
                            ApprovalRequest.document_type == "indent",
                            ApprovalRequest.document_id == ind.id
                        )
                        res_req = await db.execute(q_req)
                        req = res_req.scalar_one_or_none()
                        if req:
                            print(f"  Approval Request: ID={req.id}, Status={req.status}, Current Level={req.current_level}, Total Levels={req.total_levels}, WorkflowID={req.workflow_id}")
                            for u_2131 in users_2131:
                                can_app = await can_user_approve(db, req.id, u_2131.id)
                                print(f"    Can User {u_2131.username} (ID={u_2131.id}) Approve? {can_app}")
                        else:
                            print("  No Approval Request found for this indent!")

        # Let's inspect project workflow configs for projects involved
        project_ids = set()
        if p2178 and p2178.project_id: project_ids.add(p2178.project_id)
        if p2131 and p2131.project_id: project_ids.add(p2131.project_id)
        
        print(f"\n=== WORKFLOW CONFIGS FOR PROJECTS {list(project_ids)} ===")
        for pid in project_ids:
            if pid is None: continue
            q_cfg = select(ProjectWorkflowConfig).where(ProjectWorkflowConfig.project_id == pid)
            res_cfg = await db.execute(q_cfg)
            cfgs = res_cfg.scalars().all()
            print(f"Project ID {pid}:")
            for c in cfgs:
                print(f"  Role ID {c.role_id}: indent_approve={c.indent_approve}, indent_view={c.indent_view}")

asyncio.run(run_inspection())
