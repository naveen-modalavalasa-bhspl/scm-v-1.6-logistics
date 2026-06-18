"""
Apply multi-level dispatch changes to backend/app/api/v1/logistics.py.
"""
import sys
sys.path.insert(0, '.')
filepath = 'backend/app/api/v1/logistics.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# 1. Add photo column migrations
old1 = (
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "receiving_remarks", "TEXT NULL")\n\n'
    '    # Modify logistics_sub_dispatch_orders status column type from Enum to VARCHAR (safe upgrade)'
)
new1 = (
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "receiving_remarks", "TEXT NULL")\n'
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "handover_photos", "JSON NULL")\n'
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "handover_signature", "VARCHAR(500) NULL")\n'
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "receipt_photos", "JSON NULL")\n'
    '    await add_column_if_not_exists("logistics_sub_dispatch_orders", "receipt_signature", "VARCHAR(500) NULL")\n\n'
    '    # Modify logistics_sub_dispatch_orders status column type from Enum to VARCHAR (safe upgrade)'
)
assert old1 in content, f"Cannot find anchor 1"
content = content.replace(old1, new1, 1)
changes += 1
print(f"1. Photo column migrations added")

# 2. Add helpers + preview endpoint after resolve_mdo_project_id
old2 = '    return None\n\n\n@router.post("/mdo")'

new2_helper_block = """
async def resolve_indent_creator_position(db: AsyncSession, indent_id, material_issue_id):
    \"\"\"Resolve the indent creator's position for chain building.\"\"\"
    from app.models.indent import Indent
    from app.models.issue import MaterialIssue
    from app.models.settings_master import Employee
    from app.models.user import User
    
    indent_obj = None
    if indent_id:
        res = await db.execute(select(Indent).where(Indent.id == indent_id))
        indent_obj = res.scalar_one_or_none()
    if not indent_obj and material_issue_id:
        res = await db.execute(select(MaterialIssue).where(MaterialIssue.id == material_issue_id))
        mi = res.scalar_one_or_none()
        if mi and mi.indent_id:
            res2 = await db.execute(select(Indent).where(Indent.id == mi.indent_id))
            indent_obj = res2.scalar_one_or_none()
    if not indent_obj:
        return None
    
    user_res = await db.execute(select(User).where(User.id == indent_obj.raised_by))
    user_obj = user_res.scalar_one_or_none()
    if user_obj and user_obj.employee_id:
        emp_res = await db.execute(select(Employee).where(Employee.id == user_obj.employee_id))
        emp = emp_res.scalar_one_or_none()
        if emp and emp.position_id:
            return emp.position_id
    return None


async def build_logistics_custody_chain(
    db: AsyncSession,
    project_id: int,
    starting_position_id: int,
    dest_pos_id = None,
) -> list:
    \"\"\"Build custody chain from starting position walking UP parents.\"\"\"
    from app.models.settings_master import Position
    from app.models.approval import ProjectWorkflowConfig
    from app.services.approval_service import get_position_ancestors
    
    ancestors = await get_position_ancestors(db, starting_position_id)
    chain = []
    for pos in ancestors:
        if not pos.role_id:
            continue
        cfg_q = await db.execute(
            select(ProjectWorkflowConfig).where(
                ProjectWorkflowConfig.project_id == project_id,
                ProjectWorkflowConfig.role_id == pos.role_id
            )
        )
        cfg = cfg_q.scalar_one_or_none()
        if cfg and (cfg.dispatch_approve or cfg.dispatch_view):
            chain.append({
                "position": pos,
                "can_approve": cfg.dispatch_approve,
                "can_view": cfg.dispatch_view,
            })
    
    chain.reverse()
    
    if dest_pos_id and (not chain or chain[-1]["position"].id != dest_pos_id):
        dest_res = await db.execute(select(Position).where(Position.id == dest_pos_id))
        dest_pos = dest_res.scalar_one_or_none()
        if dest_pos:
            chain.append({
                "position": dest_pos,
                "can_approve": False,
                "can_view": False,
                "is_destination": True,
            })
    
    return chain


@router.get("/preview-dispatch-chain")
async def preview_dispatch_chain(
    material_issue_id: int = Query(...),
    destination_warehouse_id = Query(None),
    destination_user_id = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    \"\"\"Preview the multi-level dispatch chain before creating MDO.\"\"\"
    from app.models.issue import MaterialIssue
    from app.models.settings_master import Position, Employee
    from app.models.warehouse import Warehouse
    from app.api.v1.dispatch import get_destination_position_id
    
    mi_res = await db.execute(select(MaterialIssue).where(MaterialIssue.id == material_issue_id))
    mi = mi_res.scalar_one_or_none()
    if not mi:
        raise HTTPException(404, "Material Issue not found")
    
    wh_res = await db.execute(select(Warehouse).where(Warehouse.id == mi.warehouse_id))
    wh = wh_res.scalar_one_or_none()
    source_warehouse_name = wh.name if wh else "Unknown Warehouse"
    
    dest_pos_id = await get_destination_position_id(db, destination_warehouse_id, destination_user_id)
    project_id = await resolve_mdo_project_id(db, mi.indent_id, material_issue_id)
    starting_pos_id = await resolve_indent_creator_position(db, mi.indent_id, material_issue_id)
    
    if not project_id or not starting_pos_id:
        return {
            "source_warehouse": source_warehouse_name,
            "chain": [],
            "message": "Could not resolve project or starting position."
        }
    
    chain = await build_logistics_custody_chain(db, project_id, starting_pos_id, dest_pos_id)
    
    out = []
    for entry in chain:
        pos = entry["position"]
        emp_name = None
        emp_code = None
        if pos.employee_id:
            emp_res = await db.execute(select(Employee).where(Employee.id == pos.employee_id))
            emp = emp_res.scalar_one_or_none()
            if emp:
                emp_name = (emp.first_name or "") + " " + (emp.last_name or "")
                emp_name = emp_name.strip()
                emp_code = emp.code or emp.employee_code
        
        role_name = pos.role_name
        role_code = ""
        if pos.role_id:
            from app.models.user import Role
            role_q = await db.execute(select(Role).where(Role.id == pos.role_id))
            role_obj = role_q.scalar_one_or_none()
            if role_obj:
                role_name = role_obj.name
                role_code = role_obj.code
        
        out.append({
            "position_id": pos.id,
            "position_name": pos.name,
            "role_name": role_name,
            "role_code": role_code,
            "employee_name": emp_name,
            "employee_code": emp_code,
            "can_approve": entry.get("can_approve", False),
            "can_view": entry.get("can_view", False),
            "is_destination": entry.get("is_destination", False),
        })
    
    return {
        "source_warehouse": source_warehouse_name,
        "starting_position_id": starting_pos_id,
        "project_id": project_id,
        "chain": out,
    }


"""

new2 = "    return None\n\n" + new2_helper_block + '@router.post("/mdo")'

assert old2 in content, f"Cannot find anchor 2"
content = content.replace(old2, new2, 1)
changes += 1
print(f"2. Helpers + preview endpoint added")

# 3. Update create_mdo chain building
old3 = (
    '    dispatch_mode = (payload.dispatch_mode or "direct").lower()\n'
    '    from app.api.v1.dispatch import get_destination_position_id, build_dispatch_custody_chain\n'
    '    dest_pos_id = await get_destination_position_id(db, payload.destination_warehouse_id, dest_user_id)\n'
    '\n'
    '    chain = []\n'
    '    if dispatch_mode == "multi-level":\n'
    '        project_id = await resolve_mdo_project_id(db, payload.indent_id, payload.material_issue_id)\n'
    '        if project_id:\n'
    '            chain = await build_dispatch_custody_chain(db, project_id, payload.destination_warehouse_id, dest_user_id)\n'
    '\n'
    '    if chain:'
)
new3 = (
    '    dispatch_mode = (payload.dispatch_mode or "direct").lower()\n'
    '    from app.api.v1.dispatch import get_destination_position_id\n'
    '    dest_pos_id = await get_destination_position_id(db, payload.destination_warehouse_id, dest_user_id)\n'
    '\n'
    '    chain_data = []\n'
    '    if dispatch_mode == "multi-level":\n'
    '        project_id = await resolve_mdo_project_id(db, payload.indent_id, payload.material_issue_id)\n'
    '        starting_pos_id = await resolve_indent_creator_position(db, payload.indent_id, payload.material_issue_id)\n'
    '        if project_id and starting_pos_id:\n'
    '            chain_data = await build_logistics_custody_chain(db, project_id, starting_pos_id, dest_pos_id)\n'
    '\n'
    '    chain = [entry["position"] for entry in chain_data if entry.get("can_approve", False) or entry.get("is_destination", False)]\n'
    '\n'
    '    if chain:'
)
assert old3 in content, f"Cannot find anchor 3"
content = content.replace(old3, new3, 1)
changes += 1
print(f"3. create_mdo updated")

# 4. Update sdo_handover - add THIRD_PARTY restriction + photos
old4 = (
    '    if not emp or emp.position_id != sdo.custodian_position_id:\n'
    '        if current_user.role not in ("admin", "super_admin", "logistics_manager"):\n'
    '            raise HTTPException(403, "You do not have custody of this dispatch leg position")\n'
    '\n'
    '    sdo.status = "IN_TRANSIT"\n'
    '    sdo.handover_type = payload.handover_type\n'
    '    sdo.handed_over_by_id = current_user.id\n'
    '    sdo.handover_time = datetime.now(timezone.utc)\n'
    '    sdo.carrier_details = {\n'
    '        "vehicle_no": payload.vehicle_no,\n'
    '        "driver_name": payload.driver_name,\n'
    '        "driver_phone": payload.driver_phone,\n'
    '        "courier_name": payload.courier_name,\n'
    '        "awb_no": payload.awb_no,\n'
    '        "remarks": payload.remarks,\n'
    '        "otp": payload.otp\n'
    '    }\n'
    '    db.add(sdo)'
)
new4 = (
    '    if not emp or emp.position_id != sdo.custodian_position_id:\n'
    '        if current_user.role not in ("admin", "super_admin", "logistics_manager"):\n'
    '            raise HTTPException(403, "You do not have custody of this dispatch leg position")\n'
    '\n'
    '    # Restrict THIRD_PARTY for intermediate positions in multi-level mode\n'
    '    if payload.handover_type == "THIRD_PARTY":\n'
    '        res_mdo_check = await db.execute(select(LogisticsMainDispatchOrder).where(LogisticsMainDispatchOrder.id == sdo.mdo_id))\n'
    '        mdo_check = res_mdo_check.scalar_one_or_none()\n'
    '        if mdo_check and mdo_check.dispatch_mode == "multi-level":\n'
    '            res_last = await db.execute(\n'
    '                select(func.max(LogisticsSubDispatchOrder.sequence_number))\n'
    '                .where(LogisticsSubDispatchOrder.mdo_id == sdo.mdo_id)\n'
    '            )\n'
    '            max_seq = res_last.scalar() or 0\n'
    '            if sdo.sequence_number < max_seq:\n'
    '                raise HTTPException(400, "THIRD_PARTY handover is not allowed for intermediate positions. Use OWN_VEHICLE, COURIER, or IN_PERSON.")\n'
    '\n'
    '    sdo.status = "IN_TRANSIT"\n'
    '    sdo.handover_type = payload.handover_type\n'
    '    sdo.handed_over_by_id = current_user.id\n'
    '    sdo.handover_time = datetime.now(timezone.utc)\n'
    '    sdo.carrier_details = {\n'
    '        "vehicle_no": payload.vehicle_no,\n'
    '        "driver_name": payload.driver_name,\n'
    '        "driver_phone": payload.driver_phone,\n'
    '        "courier_name": payload.courier_name,\n'
    '        "awb_no": payload.awb_no,\n'
    '        "remarks": payload.remarks,\n'
    '        "otp": payload.otp\n'
    '    }\n'
    '    if payload.handover_photos:\n'
    '        sdo.handover_photos = payload.handover_photos\n'
    '    if payload.handover_signature:\n'
    '        sdo.handover_signature = payload.handover_signature\n'
    '    db.add(sdo)'
)
assert old4 in content, f"Cannot find anchor 4"
content = content.replace(old4, new4, 1)
changes += 1
print(f"4. sdo_handover updated")

# 5. Update sdo_receive - add photos
old5 = (
    '    sdo.receiving_remarks = payload.receiving_remarks\n'
    '    db.add(sdo)\n'
    '\n'
    '    db.add(ActivityLog(\n'
    '        user_id=current_user.id,\n'
    '        module="logistics",\n'
    '        action="sdo_receive",'
)
new5 = (
    '    sdo.receiving_remarks = payload.receiving_remarks\n'
    '    if payload.receipt_photos:\n'
    '        sdo.receipt_photos = payload.receipt_photos\n'
    '    if payload.receipt_signature:\n'
    '        sdo.receipt_signature = payload.receipt_signature\n'
    '    db.add(sdo)\n'
    '\n'
    '    db.add(ActivityLog(\n'
    '        user_id=current_user.id,\n'
    '        module="logistics",\n'
    '        action="sdo_receive",'
)
assert old5 in content, f"Cannot find anchor 5"
content = content.replace(old5, new5, 1)
changes += 1
print(f"5. sdo_receive updated")

# 6. Update MDO response to include photo fields
old6 = (
    '                receiving_remarks=s.receiving_remarks\n'
    '            )\n'
    '            m_dict.sdos.append(s_dict)'
)
new6 = (
    '                receiving_remarks=s.receiving_remarks,\n'
    '                handover_photos=s.handover_photos,\n'
    '                handover_signature=s.handover_signature,\n'
    '                receipt_photos=s.receipt_photos,\n'
    '                receipt_signature=s.receipt_signature\n'
    '            )\n'
    '            m_dict.sdos.append(s_dict)'
)
assert old6 in content, f"Cannot find anchor 6"
content = content.replace(old6, new6, 1)
changes += 1
print(f"6. MDO response SDO photos updated")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\nAll {changes} changes applied successfully!")
