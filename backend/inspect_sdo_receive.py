import asyncio
import traceback
from datetime import datetime, timezone
from app.database import AsyncSessionLocal
from app.models.logistics import LogisticsSubDispatchOrder, LogisticsMainDispatchOrder
from app.models.settings_master import Employee as RecvEmployee, Position
from app.models.user import Role, User
from app.models.system import ActivityLog
from app.schemas.logistics import SdoReceiveSchema
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def main():
    async with AsyncSessionLocal() as session:
        sdo_id = 82
        # Mock payload
        payload = SdoReceiveSchema(
            seal_intact=True,
            packaging_condition="INTACT",
            discrepancy_reported=False,
            receiving_remarks="Inspected ok.",
            receipt_photos=[],
            receipt_signature="data:image/png;base64,..."
        )
        
        # Mock current_user
        res_user = await session.execute(
            select(User).where(User.id == 22) # Let's assume user ID 22 (creator or active user)
        )
        current_user = res_user.scalar_one_or_none()
        
        try:
            res = await session.execute(
                select(LogisticsSubDispatchOrder)
                .options(selectinload(LogisticsSubDispatchOrder.mdo))
                .where(LogisticsSubDispatchOrder.id == sdo_id)
            )
            sdo = res.scalar_one_or_none()
            if not sdo:
                print("SDO not found")
                return

            mdo = sdo.mdo
            print("MDO loaded:", mdo.mdo_number)
            
            sdo.status = "ACKNOWLEDGED"
            sdo.received_by_id = current_user.id
            sdo.received_at = datetime.now(timezone.utc)
            sdo.seal_intact = payload.seal_intact
            sdo.packaging_condition = payload.packaging_condition
            sdo.discrepancy_reported = payload.discrepancy_reported
            sdo.receiving_remarks = payload.receiving_remarks
            
            # Resolve role code
            role_code = "CUSTODIAN"
            pos_q = await session.execute(select(Position).where(Position.id == sdo.custodian_position_id))
            pos = pos_q.scalar_one_or_none()
            if pos and pos.role_id:
                role_q = await session.execute(select(Role).where(Role.id == pos.role_id))
                role_obj = role_q.scalar_one_or_none()
                if role_obj:
                    role_code = role_obj.code
            mdo.status = f"AT_{role_code.upper()}"
            print("MDO status set to:", mdo.status)
            
            # Resolve custody chain to check if this is the final leg
            from app.api.v1.dispatch import get_destination_position_id
            print("Getting destination position ID...")
            dest_pos_id = await get_destination_position_id(session, mdo.destination_warehouse_id, mdo.destination_user_id)
            print("Destination position ID:", dest_pos_id)
            
            from app.api.v1.logistics import resolve_mdo_project_id, resolve_indent_creator_position, build_logistics_custody_chain
            print("Resolving project ID...")
            project_id = await resolve_mdo_project_id(session, mdo.indent_id, mdo.material_issue_id)
            print("Project ID:", project_id)
            print("Resolving starting position ID...")
            starting_pos_id = await resolve_indent_creator_position(session, mdo.indent_id, mdo.material_issue_id)
            print("Starting position ID:", starting_pos_id)

            chain_data = []
            if mdo.dispatch_mode == "multi-level" and project_id and starting_pos_id:
                print("Building custody chain...")
                chain_data = await build_logistics_custody_chain(session, project_id, starting_pos_id, dest_pos_id)
            
            chain = [entry["position"] for entry in chain_data if entry.get("can_approve", False) or entry.get("is_destination", False)]
            print("Chain size:", len(chain))

            is_last_leg = False
            if not chain or sdo.sequence_number >= len(chain):
                is_last_leg = True
            print("Is last leg:", is_last_leg)

            if is_last_leg:
                print("Processing last leg logic...")
                mdo.status = "COMPLETED"
                await session.flush()

                from app.models.dispatch import DispatchOrder, DispatchOrderItem
                disp_check = await session.execute(select(DispatchOrder).where(DispatchOrder.dispatch_number == mdo.mdo_number))
                disp = disp_check.scalar_one_or_none()

                if not disp:
                    print("Creating DispatchOrder...")
                    disp = DispatchOrder(
                        dispatch_number=mdo.mdo_number,
                        warehouse_id=mdo.warehouse_id,
                        destination_warehouse_id=mdo.destination_warehouse_id,
                        destination_user_id=mdo.destination_user_id,
                        destination_type="WAREHOUSE" if mdo.destination_warehouse_id else "USER",
                        dispatch_type=mdo.dispatch_type or "THIRD_PARTY",
                        status="delivered",
                        remarks=mdo.special_instructions,
                        material_issue_id=mdo.material_issue_id,
                        dispatch_date=mdo.order_date,
                        expected_delivery_date=mdo.required_delivery_date,
                        delivery_acknowledged=True,
                        delivery_acknowledged_at=datetime.now(timezone.utc),
                        delivery_acknowledged_by_name=current_user.username,
                        delivery_remarks=payload.receiving_remarks,
                        goods_condition_on_delivery="DAMAGED" if payload.discrepancy_reported else "GOOD"
                    )
                    session.add(disp)
                    await session.flush()
                    print("DispatchOrder created with ID:", disp.id)

                    from app.models.logistics import LogisticsDispatchMaterial
                    res_mats = await session.execute(select(LogisticsDispatchMaterial).where(LogisticsDispatchMaterial.mdo_id == mdo.id))
                    mats = res_mats.scalars().all()
                    print(f"Adding {len(mats)} materials...")
                    for mat in mats:
                        item = DispatchOrderItem(
                            dispatch_order_id=disp.id,
                            material_id=mat.material_id,
                            indent_id=mdo.indent_id,
                            material_issue_id=mdo.material_issue_id,
                            requested_quantity=mat.quantity,
                            approved_quantity=mat.quantity,
                            dispatched_quantity=mat.quantity,
                            uom=mat.unit_of_measure,
                            request_date=mdo.order_date
                        )
                        session.add(item)
                    await session.flush()

                from app.api.v1.dispatch import process_dispatch_stock_deduction
                print("Processing stock deduction...")
                await process_dispatch_stock_deduction(session, disp, mdo.created_by or 1)
                print("Stock deduction completed!")

            print("Commit would occur now.")
            # session.commit() -- don't actually commit in test script

        except Exception as e:
            print("ERROR CAUGHT:")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
