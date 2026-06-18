"""
Simplify the position filter subquery in get_mdos().
Instead of .subquery() + select(subquery.c.mdo_id), use .in_(select(...)) directly.
"""
with open('app/api/v1/logistics.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """    # Filter by user position in SDO custody chain (non-admin users)
    if user_position_id and not is_admin:
        subquery = (
            select(LogisticsSubDispatchOrder.mdo_id)
            .where(LogisticsSubDispatchOrder.custodian_position_id == user_position_id)
            .distinct()
        ).subquery()
        query = query.where(LogisticsMainDispatchOrder.id.in_(select(subquery.c.mdo_id)))"""

new = """    # Filter by user position in SDO custody chain (non-admin users)
    if user_position_id and not is_admin:
        query = query.where(
            LogisticsMainDispatchOrder.id.in_(
                select(LogisticsSubDispatchOrder.mdo_id)
                .where(LogisticsSubDispatchOrder.custodian_position_id == user_position_id)
            )
        )"""

if old in content:
    content = content.replace(old, new, 1)
    print("SUCCESS: Subquery simplified")
else:
    print("FAIL: Could not find the old subquery block")

with open('app/api/v1/logistics.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("File saved.")
