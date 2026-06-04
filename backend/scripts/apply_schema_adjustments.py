"""Apply small idempotent schema adjustments for the current codebase.

This script only adds missing columns/tables used by SQLAlchemy models. It does
not drop or rewrite data, and every change is checked through information_schema
before execution.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymysql
from app.config import settings


def connect():
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        autocommit=True,
        charset="utf8mb4",
    )


def table_exists(cur, table_name):
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        (table_name,),
    )
    return cur.fetchone()[0] > 0


def column_exists(cur, table_name, column_name):
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    return cur.fetchone()[0] > 0


def constraint_exists(cur, constraint_name):
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.table_constraints
        WHERE constraint_schema = DATABASE()
          AND constraint_name = %s
        """,
        (constraint_name,),
    )
    return cur.fetchone()[0] > 0


def run(cur, sql, label):
    print(f"Applying: {label}")
    cur.execute(sql)


def add_column(cur, table_name, column_name, ddl):
    if not table_exists(cur, table_name):
        print(f"Skipping {table_name}.{column_name}: table does not exist")
        return
    if column_exists(cur, table_name, column_name):
        print(f"Already present: {table_name}.{column_name}")
        return
    run(cur, f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {ddl}", f"{table_name}.{column_name}")


def add_fk(cur, constraint_name, table_name, column_name, ref_table, ref_column="id", on_delete=None):
    if constraint_exists(cur, constraint_name):
        print(f"Already present: constraint {constraint_name}")
        return
    if not (table_exists(cur, table_name) and table_exists(cur, ref_table)):
        print(f"Skipping constraint {constraint_name}: required table missing")
        return
    suffix = f" ON DELETE {on_delete}" if on_delete else ""
    run(
        cur,
        (
            f"ALTER TABLE `{table_name}` ADD CONSTRAINT `{constraint_name}` "
            f"FOREIGN KEY (`{column_name}`) REFERENCES `{ref_table}` (`{ref_column}`){suffix}"
        ),
        f"constraint {constraint_name}",
    )


def create_grn_item_serials(cur):
    if table_exists(cur, "grn_item_serials"):
        print("Already present: grn_item_serials")
        return
    run(
        cur,
        """
        CREATE TABLE `grn_item_serials` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `grn_item_id` BIGINT NOT NULL,
            `serial_number` VARCHAR(100) NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_grn_item_serials_grn_item_id` (`grn_item_id`),
            CONSTRAINT `fk_grn_item_serials_grn_item_id`
                FOREIGN KEY (`grn_item_id`) REFERENCES `grn_items` (`id`)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        "table grn_item_serials",
    )


def main():
    changes = [
        ("material_issues", "destination_warehouse_id", "BIGINT NULL"),
        ("quotation_items", "cgst_rate", "DECIMAL(5, 2) NULL DEFAULT 0"),
        ("quotation_items", "sgst_rate", "DECIMAL(5, 2) NULL DEFAULT 0"),
        ("quotation_items", "igst_rate", "DECIMAL(5, 2) NULL DEFAULT 0"),
        ("quotations", "cgst_amount", "DECIMAL(15, 2) NULL DEFAULT 0"),
        ("quotations", "sgst_amount", "DECIMAL(15, 2) NULL DEFAULT 0"),
        ("quotations", "igst_amount", "DECIMAL(15, 2) NULL DEFAULT 0"),
        ("stock_balance", "transit_qty", "DECIMAL(15, 3) NULL DEFAULT 0"),
    ]
    with connect() as conn:
        with conn.cursor() as cur:
            for table_name, column_name, ddl in changes:
                add_column(cur, table_name, column_name, ddl)
            add_fk(
                cur,
                "fk_material_issues_destination_warehouse_id",
                "material_issues",
                "destination_warehouse_id",
                "warehouses",
                on_delete="SET NULL",
            )
            create_grn_item_serials(cur)
    print("Schema adjustments complete.")


if __name__ == "__main__":
    main()
