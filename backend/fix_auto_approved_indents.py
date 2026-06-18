"""
Fix Indents 68, 69, 70 — Reset auto-approved / stuck approval requests
so they can be re-submitted through the new hierarchical workflow.

WARNING: This modifies data. Read the dry-run output first, then
pass --apply to actually execute the changes.
"""
import sys, pymysql, argparse
sys.path.insert(0, '.')
from app.config import settings

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true", help="Actually apply changes (default is dry-run)")
args = parser.parse_args()

conn = pymysql.connect(
    host=settings.DB_HOST, port=settings.DB_PORT,
    user=settings.DB_USER, password=settings.DB_PASSWORD,
    database=settings.DB_NAME, charset='utf8mb4'
)
c = conn.cursor()

INDENT_IDS = (68, 69, 70)

print("=" * 70)
print("CURRENT STATE")
print("=" * 70)

# Indents
c.execute("""
    SELECT i.id, i.indent_number, i.status, i.raised_by, i.project_id,
           i.warehouse_id
    FROM indents i WHERE i.id IN %s ORDER BY i.id
""", (INDENT_IDS,))
indents = {row[0]: row for row in c.fetchall()}
for row in indents.values():
    print(f"\n  Indent #{row[0]}: '{row[1]}'")
    print(f"    status={row[2]}, raised_by={row[3]}, project={row[4]}, wh={row[5]}")

# Approval requests
c.execute("""
    SELECT ar.id, ar.document_id, ar.status, ar.total_levels, ar.workflow_id,
           ar.requested_by, ar.completed_at
    FROM approval_requests ar
    WHERE ar.document_type = 'indent'
      AND ar.document_id IN %s
    ORDER BY ar.document_id
""", (INDENT_IDS,))
approval_requests = c.fetchall()
if approval_requests:
    print(f"\n  Approval requests to delete:")
    for row in approval_requests:
        print(f"    AR #{row[0]}: doc_id={row[1]}, status={row[2]}, total_levels={row[3]}, wf={row[4]}")
else:
    print("\n  No approval requests found.")

# History records
if approval_requests:
    ar_ids = tuple(r[0] for r in approval_requests)
    c.execute("""
        SELECT COUNT(*) FROM approval_history
        WHERE request_id IN %s
    """, (ar_ids,))
    hist_count = c.fetchone()[0]
    print(f"\n  Approval history records to delete: {hist_count}")

print()
print("=" * 70)
print("CHANGES TO MAKE")
print("=" * 70)
print("""
  1. Delete approval_history records linked to these approval requests
  2. Delete the approval_requests themselves
  3. Reset indent status to 'draft'
""")

if not args.apply:
    print(">>> DRY-RUN MODE <<<")
    print("Run with --apply to execute changes.")
    conn.close()
    sys.exit(0)

# ===== EXECUTE =====
print(">>> APPLYING CHANGES <<<")

try:
    # Step 1: Delete history
    if approval_requests:
        ar_ids = tuple(r[0] for r in approval_requests)
        c.execute("""
            DELETE FROM approval_history WHERE request_id IN %s
        """, (ar_ids,))
        print(f"  ✅ Deleted {c.rowcount} approval_history record(s)")

        # Step 2: Delete approval requests
        c.execute("""
            DELETE FROM approval_requests WHERE id IN %s
        """, (ar_ids,))
        print(f"  ✅ Deleted {c.rowcount} approval_request record(s)")

    # Step 3: Reset indents to draft
    c.execute("""
        UPDATE indents SET status = 'draft' WHERE id IN %s
    """, (INDENT_IDS,))
    print(f"  ✅ Reset {c.rowcount} indent(s) to 'draft' status")

    conn.commit()
    print("\n✅ ALL CHANGES COMMITTED SUCCESSFULLY")
    print("\n  Next steps:")
    print("  1. Fix the position hierarchy (Update position 3049's parent to 2131)")
    print("  2. Re-submit the indents through the UI (or API)")
    print("  3. The hierarchical workflow should now route through OE → DM → RM → SPH")

except Exception as e:
    conn.rollback()
    print(f"\n❌ ERROR: {e}")
    print("Changes rolled back.")
    sys.exit(1)

finally:
    conn.close()
