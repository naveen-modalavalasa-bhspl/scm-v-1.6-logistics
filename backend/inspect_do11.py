
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = "mysql+aiomysql://root:rolex@localhost:3306/bhspl_scm"

async def inspect():
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.connect() as conn:
        # MDO
        r = await conn.execute(text(
            "SELECT m.id, m.mdo_number, m.dispatch_mode, m.dispatch_type, m.status,"
            " m.destination_warehouse_id, m.destination_user_id, m.material_issue_id, m.indent_id"
            " FROM logistics_main_dispatch_orders m"
            " WHERE m.mdo_number = 'DO-2026-0000011'"
        ))
        mdo = r.fetchone()
        if not mdo:
            print("MDO DO-2026-0000011 not found!")
            return
        mdo = dict(mdo._mapping)
        print("=== MDO ===")
        print(mdo)

        mdo_id = mdo['id']

        # SDOs
        r2 = await conn.execute(text(
            "SELECT s.id, s.sdo_number, s.sequence_number, s.status,"
            " s.custodian_position_id, p.name as pos_name, p.employee_id as pos_emp_id,"
            " ro.code as role_code,"
            " s.handed_over_by_id, s.received_by_id"
            f" FROM logistics_sub_dispatch_orders s"
            " LEFT JOIN positions p ON p.id = s.custodian_position_id"
            " LEFT JOIN roles ro ON ro.id = p.role_id"
            f" WHERE s.mdo_id = {mdo_id}"
            " ORDER BY s.sequence_number"
        ))
        sdos = r2.fetchall()
        print("\n=== SDOs ===")
        for s in sdos:
            print(dict(s._mapping))

        # Destination user
        dest_user_id = mdo.get('destination_user_id')
        if dest_user_id:
            r3 = await conn.execute(text(
                "SELECT u.id, u.username, u.employee_id,"
                " e.name as emp_name, e.position_id as active_pos_id,"
                " p.name as active_pos_name, p.role_id,"
                " ro.code as role_code"
                " FROM users u"
                " LEFT JOIN employees e ON e.id = u.employee_id"
                " LEFT JOIN positions p ON p.id = e.position_id"
                " LEFT JOIN roles ro ON ro.id = p.role_id"
                f" WHERE u.id = {dest_user_id}"
            ))
            du = r3.fetchone()
            print("\n=== DESTINATION USER ===")
            print(dict(du._mapping) if du else "Not found")

            # All positions for destination employee
            if du:
                du = dict(du._mapping)
                emp_id = du.get('employee_id')
                if emp_id:
                    rp = await conn.execute(text(
                        "SELECT p.id, p.name, p.role_id, ro.code as role_code, p.employee_id"
                        " FROM positions p"
                        " LEFT JOIN roles ro ON ro.id = p.role_id"
                        f" WHERE p.employee_id = {emp_id}"
                    ))
                    all_pos = rp.fetchall()
                    print("  All positions for destination employee:")
                    for ap in all_pos:
                        print(" ", dict(ap._mapping))

        # Material issue -> indent -> project
        material_issue_id = mdo.get('material_issue_id')
        if material_issue_id:
            r4 = await conn.execute(text(
                "SELECT mi.id, mi.indent_id, i.project_id, i.raised_by"
                " FROM material_issues mi"
                " LEFT JOIN indents i ON i.id = mi.indent_id"
                f" WHERE mi.id = {material_issue_id}"
            ))
            mi = r4.fetchone()
            print("\n=== MATERIAL ISSUE -> INDENT -> PROJECT ===")
            print(dict(mi._mapping) if mi else "Not found")

            if mi:
                mi = dict(mi._mapping)
                project_id = mi.get('project_id')
                raised_by = mi.get('raised_by')

                if project_id:
                    r5 = await conn.execute(text(
                        "SELECT pwc.role_id, ro.code as role_code, ro.name as role_name,"
                        " pwc.dispatch_approve, pwc.dispatch_view"
                        " FROM project_workflow_configs pwc"
                        " LEFT JOIN roles ro ON ro.id = pwc.role_id"
                        f" WHERE pwc.project_id = {project_id}"
                        " ORDER BY pwc.id"
                    ))
                    cfgs = r5.fetchall()
                    print("\n=== WORKFLOW CONFIG (all roles) ===")
                    for c in cfgs:
                        print(dict(c._mapping))

                if raised_by:
                    ic_r = await conn.execute(text(
                        "SELECT u.id, u.username, e.id as emp_id, e.position_id, p.name as pos_name, p.parent_position_id, ro.code as role_code"
                        " FROM users u"
                        " LEFT JOIN employees e ON e.id = u.employee_id"
                        " LEFT JOIN positions p ON p.id = e.position_id"
                        " LEFT JOIN roles ro ON ro.id = p.role_id"
                        f" WHERE u.id = {raised_by}"
                    ))
                    ic = ic_r.fetchone()
                    print("\n=== INDENT CREATOR (starting position) ===")
                    print(dict(ic._mapping) if ic else "Not found")

                    if ic:
                        ic = dict(ic._mapping)
                        start_pos_id = ic.get('position_id')
                        print("\n=== ANCESTOR CHAIN OF STARTING POSITION ===")
                        pos_id = start_pos_id
                        depth = 0
                        while pos_id and depth < 12:
                            pr = await conn.execute(text(
                                "SELECT p.id, p.name, p.parent_position_id, p.employee_id, p.role_id,"
                                " ro.code as role_code,"
                                " pwc.dispatch_approve, pwc.dispatch_view"
                                " FROM positions p"
                                " LEFT JOIN roles ro ON ro.id = p.role_id"
                                " LEFT JOIN project_workflow_configs pwc"
                                f"   ON pwc.role_id = p.role_id AND pwc.project_id = {project_id}"
                                f" WHERE p.id = {pos_id}"
                            ))
                            pos_row = pr.fetchone()
                            if not pos_row:
                                break
                            pos_row = dict(pos_row._mapping)
                            indent = "  " * depth
                            print(f"{indent}-> pos_id={pos_row['id']} name={pos_row['name']} role={pos_row['role_code']} approve={pos_row['dispatch_approve']} view={pos_row['dispatch_view']}")
                            pos_id = pos_row['parent_position_id']
                            depth += 1

asyncio.run(inspect())
