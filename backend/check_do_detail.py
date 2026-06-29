"""Check DispatchOrder DO-BHSPL-FY26-27-0000000114 details."""
import asyncio
from app.database import engine
from sqlalchemy import text

async def run():
    async with engine.connect() as conn:
        # Find dispatch order
        res = await conn.execute(text(
            "SELECT * FROM dispatch_orders WHERE dispatch_number = 'DO-BHSPL-FY26-27-0000000114'"
        ))
        do_row = res.fetchone()
        if not do_row:
            print("DispatchOrder not found!")
            return
        do = dict(do_row._mapping)
        print("DispatchOrder DO-BHSPL-FY26-27-0000000114:")
        for k, v in do.items():
            print(f"  {k}: {v}")
            
        # Find linked material issue
        mi_id = do.get("material_issue_id")
        if mi_id:
            res_mi = await conn.execute(text(
                f"SELECT * FROM material_issues WHERE id = {mi_id}"
            ))
            mi_row = res_mi.fetchone()
            if mi_row:
                print("\nLinked MaterialIssue:")
                for k, v in dict(mi_row._mapping).items():
                    print(f"  {k}: {v}")
                    
        # Find consignments linked to this material_issue_id
        if mi_id:
            res_con = await conn.execute(text(
                f"SELECT * FROM consignments WHERE material_issue_id = {mi_id}"
            ))
            con_rows = res_con.fetchall()
            print(f"\nLinked Consignments ({len(con_rows)}):")
            for c in con_rows:
                con = dict(c._mapping)
                print(f"  Consignment {con['id']}: number={con['consignment_number']}, status={con['status']}, mdo_id={con['mdo_id']}")
                
        # Find LogisticsMainDispatchOrder linked by dispatch_number
        dn = do.get("dispatch_number")
        if dn:
            res_mdo = await conn.execute(text(
                "SELECT * FROM logistics_main_dispatch_orders WHERE mdo_number = :dn OR id = :mdo_id",
            ), {"dn": dn, "mdo_id": do.get("mdo_id") or -1})
            mdo_rows = res_mdo.fetchall()
            print(f"\nLinked Main Dispatch Orders ({len(mdo_rows)}):")
            for m in mdo_rows:
                mdo = dict(m._mapping)
                print(f"  MDO {mdo['id']}: number={mdo['mdo_number']}, status={mdo['status']}")

asyncio.run(run())
