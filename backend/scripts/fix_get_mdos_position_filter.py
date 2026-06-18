"""
Fix get_mdos() to filter by user's position in the SDO custody chain.
Users with a position (via employee → position_id) will only see MDOs
where their position appears in any SDO's custodian_position_id.
Admin/super_admin roles bypass this filter.
"""
import re

with open('app/api/v1/logistics.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the get_mdos function start
old_func_start = """@router.get("/mdo", response_model=List[MdoResponse])
async def get_mdos(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    res = await db.execute(
        select(LogisticsMainDispatchOrder)
        .options("""

new_func_start = """@router.get("/mdo", response_model=List[MdoResponse])
async def get_mdos(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Resolve user's position for SDO-based filtering
    from app.models.settings_master import Employee as MdoEmployee
    user_position_id = None
    if current_user.employee_id:
        emp_res = await db.execute(select(MdoEmployee).where(MdoEmployee.id == current_user.employee_id))
        emp = emp_res.scalar_one_or_none()
        if emp and emp.position_id:
            user_position_id = emp.position_id
    
    # Admin/super_admin bypass position filter
    from app.utils.dependencies import get_user_role_codes
    role_codes = set(await get_user_role_codes(db, current_user.id))
    is_admin = bool({"super_admin", "admin"} & role_codes)
    
    query = (
        select(LogisticsMainDispatchOrder)
        .options(
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.custodian_position),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.handed_over_by),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.received_by),
            selectinload(LogisticsMainDispatchOrder.materials).joinedload(LogisticsDispatchMaterial.material),
            selectinload(LogisticsMainDispatchOrder.handover).joinedload(DispatchHandover.transporter),
            joinedload(LogisticsMainDispatchOrder.warehouse),
            joinedload(LogisticsMainDispatchOrder.destination_user),
            joinedload(LogisticsMainDispatchOrder.creator)
        )
    )
    
    # Filter by user position in SDO custody chain (non-admin users)
    if user_position_id and not is_admin:
        subquery = (
            select(LogisticsSubDispatchOrder.mdo_id)
            .where(LogisticsSubDispatchOrder.custodian_position_id == user_position_id)
            .distinct()
        ).subquery()
        query = query.where(LogisticsMainDispatchOrder.id.in_(select(subquery.c.mdo_id)))
    
    query = query.order_by(LogisticsMainDispatchOrder.id.desc())
    res = await db.execute(query)"""

# Find the exact match
idx = content.find(old_func_start)
if idx >= 0:
    # Find the end of the old function (the line "    mdos = res.scalars().all()")
    # We need to find just the select() part to replace
    old_select_block = """    res = await db.execute(
        select(LogisticsMainDispatchOrder)
        .options(
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.custodian_position),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.handed_over_by),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.received_by),
            selectinload(LogisticsMainDispatchOrder.materials).joinedload(LogisticsDispatchMaterial.material),
            selectinload(LogisticsMainDispatchOrder.handover).joinedload(DispatchHandover.transporter),
            joinedload(LogisticsMainDispatchOrder.warehouse),
            joinedload(LogisticsMainDispatchOrder.destination_user),
            joinedload(LogisticsMainDispatchOrder.creator)
        )
        .order_by(LogisticsMainDispatchOrder.id.desc())
    )"""

    new_select_block = """    # Resolve user's position for SDO-based filtering
    from app.models.settings_master import Employee as MdoEmployee
    user_position_id = None
    if current_user.employee_id:
        emp_res = await db.execute(select(MdoEmployee).where(MdoEmployee.id == current_user.employee_id))
        emp = emp_res.scalar_one_or_none()
        if emp and emp.position_id:
            user_position_id = emp.position_id
    
    # Admin/super_admin bypass position filter
    from app.utils.dependencies import get_user_role_codes
    role_codes = set(await get_user_role_codes(db, current_user.id))
    is_admin = bool({"super_admin", "admin"} & role_codes)
    
    query = (
        select(LogisticsMainDispatchOrder)
        .options(
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.custodian_position),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.handed_over_by),
            selectinload(LogisticsMainDispatchOrder.sdos).joinedload(LogisticsSubDispatchOrder.received_by),
            selectinload(LogisticsMainDispatchOrder.materials).joinedload(LogisticsDispatchMaterial.material),
            selectinload(LogisticsMainDispatchOrder.handover).joinedload(DispatchHandover.transporter),
            joinedload(LogisticsMainDispatchOrder.warehouse),
            joinedload(LogisticsMainDispatchOrder.destination_user),
            joinedload(LogisticsMainDispatchOrder.creator)
        )
    )
    
    # Filter by user position in SDO custody chain (non-admin users)
    if user_position_id and not is_admin:
        subquery = (
            select(LogisticsSubDispatchOrder.mdo_id)
            .where(LogisticsSubDispatchOrder.custodian_position_id == user_position_id)
            .distinct()
        ).subquery()
        query = query.where(LogisticsMainDispatchOrder.id.in_(select(subquery.c.mdo_id)))
    
    query = query.order_by(LogisticsMainDispatchOrder.id.desc())
    res = await db.execute(query)"""

    if old_select_block in content:
        content = content.replace(old_select_block, new_select_block, 1)
        print("SUCCESS: Position-based filter added to get_mdos()")
    else:
        print("FAIL: Could not find the old select block. Checking snippet...")
        # Debug: show the actual snippet around that area
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'select(LogisticsMainDispatchOrder)' in line:
                # Print 3 lines before and 5 lines after
                for j in range(max(0, i-1), min(len(lines), i+10)):
                    print(f"  {j+1}: {lines[j]}")
else:
    print("FAIL: Could not find get_mdos function")

with open('app/api/v1/logistics.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("File saved.")
