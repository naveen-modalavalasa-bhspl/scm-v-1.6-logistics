"""
Fix auth logic:
1. sdo_handover: Allow origin warehouse user for SDO 1, or previous SDO's custodian for SDO > 1
2. sdo_receive: Add position auth check matching SDO's custodian_position_id
"""
filepath = 'backend/app/api/v1/logistics.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# Fix 1: sdo_handover auth - replace the position check block
old_handover_auth = (
    '    from app.models.settings_master import Employee\n'
    '    emp_res = await db.execute(\n'
    '        select(Employee).where(Employee.id == current_user.employee_id)\n'
    '    )\n'
    '    emp = emp_res.scalar_one_or_none()\n'
    '    if not emp or emp.position_id != sdo.custodian_position_id:\n'
    '        if current_user.role not in ("admin", "super_admin", "logistics_manager"):\n'
    '            raise HTTPException(403, "You do not have custody of this dispatch leg position")\n'
    '\n'
    '    # Restrict THIRD_PARTY for intermediate positions in multi-level mode'
)

new_handover_auth = (
    '    # Auth check: For SDO 1, allow origin warehouse user. For SDO > 1, must be previous custodian.\n'
    '    from app.models.settings_master import Employee, Position as SdoPosition\n'
    '    from app.models.warehouse import Warehouse as SdoWarehouse\n'
    '    res_mdo_for_auth = await db.execute(select(LogisticsMainDispatchOrder).where(LogisticsMainDispatchOrder.id == sdo.mdo_id))\n'
    '    mdo_for_auth = res_mdo_for_auth.scalar_one_or_none()\n'
    '    \n'
    '    is_authorized = False\n'
    '    if current_user.role in ("admin", "super_admin", "logistics_manager"):\n'
    '        is_authorized = True\n'
    '    elif sdo.sequence_number == 1 and mdo_for_auth:\n'
    '        # Origin warehouse user can handover SDO 1\n'
    '        uw_check = await db.execute(\n'
    '            select(UserWarehouse).where(\n'
    '                UserWarehouse.user_id == current_user.id,\n'
    '                UserWarehouse.warehouse_id == mdo_for_auth.warehouse_id\n'
    '            )\n'
    '        )\n'
    '        if uw_check.scalar_one_or_none():\n'
    '            is_authorized = True\n'
    '    elif sdo.sequence_number > 1:\n'
    '        # User must be the custodian of the previous SDO (they received it)\n'
    '        prev_sdo_res = await db.execute(\n'
    '            select(LogisticsSubDispatchOrder)\n'
    '            .where(\n'
    '                LogisticsSubDispatchOrder.mdo_id == sdo.mdo_id,\n'
    '                LogisticsSubDispatchOrder.sequence_number == sdo.sequence_number - 1\n'
    '            )\n'
    '            .limit(1)\n'
    '        )\n'
    '        prev_sdo = prev_sdo_res.scalar_one_or_none()\n'
    '        if prev_sdo and prev_sdo.received_by_id == current_user.id:\n'
    '            is_authorized = True\n'
    '    \n'
    '    if not is_authorized:\n'
    '        raise HTTPException(403, "You are not authorized to handover this dispatch leg")\n'
    '\n'
    '    # Restrict THIRD_PARTY for intermediate positions in multi-level mode'
)

assert old_handover_auth in content, "Cannot find handover auth block"
content = content.replace(old_handover_auth, new_handover_auth, 1)
changes += 1
print(f"1. sdo_handover auth fixed ✓")

# Fix 2: sdo_receive - add position auth check
old_receive_auth = (
    '    sdo = res.scalar_one_or_none()\n'
    '    if not sdo:\n'
    '        raise HTTPException(404, "Sub-dispatch order leg not found")\n'
    '\n'
    '    mdo = sdo.mdo\n'
    '    if not mdo:\n'
    '        raise HTTPException(404, "Parent MDO not found")\n'
    '\n'
    '    sdo.status = "RECEIVED"\n'
    '    sdo.received_by_id = current_user.id'
)

new_receive_auth = (
    '    sdo = res.scalar_one_or_none()\n'
    '    if not sdo:\n'
    '        raise HTTPException(404, "Sub-dispatch order leg not found")\n'
    '\n'
    '    mdo = sdo.mdo\n'
    '    if not mdo:\n'
    '        raise HTTPException(404, "Parent MDO not found")\n'
    '\n'
    '    # Auth check: user must occupy the custodian position for this SDO\n'
    '    from app.models.settings_master import Employee as RecvEmployee\n'
    '    recv_emp_res = await db.execute(\n'
    '        select(RecvEmployee).where(RecvEmployee.id == current_user.employee_id)\n'
    '    )\n'
    '    recv_emp = recv_emp_res.scalar_one_or_none()\n'
    '    if not recv_emp or recv_emp.position_id != sdo.custodian_position_id:\n'
    '        if current_user.role not in ("admin", "super_admin", "logistics_manager"):\n'
    '            raise HTTPException(403, "You do not occupy the required position to receive this dispatch leg")\n'
    '\n'
    '    sdo.status = "RECEIVED"\n'
    '    sdo.received_by_id = current_user.id'
)

assert old_receive_auth in content, "Cannot find receive auth anchor"
content = content.replace(old_receive_auth, new_receive_auth, 1)
changes += 1
print(f"2. sdo_receive auth added ✓")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\nAll {changes} changes applied!")
