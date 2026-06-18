import sys, pymysql
sys.path.insert(0, '.')
from app.config import settings

conn = pymysql.connect(
    host=settings.DB_HOST, port=settings.DB_PORT,
    user=settings.DB_USER, password=settings.DB_PASSWORD,
    database=settings.DB_NAME, charset='utf8mb4'
)
c = conn.cursor()

# Check approval_requests columns
print("=== approval_requests columns ===")
c.execute("DESCRIBE approval_requests")
cols = c.fetchall()
for row in cols:
    print(f"  {row[0]} ({row[1]})")

# Check what history-like tables exist
print("\n=== tables matching '%approval%' ===")
c.execute("SHOW TABLES LIKE '%approval%'")
for row in c.fetchall():
    print(f"  {row[0]}")

# Check approval_requests for indents 68, 69, 70
print("\n=== ApprovalRequests for indents 68, 69, 70 ===")
c.execute("""
    SELECT ar.id, ar.document_id, ar.document_number, ar.status,
           ar.current_level, ar.total_levels, ar.workflow_id,
           ar.requested_by, ar.completed_at, ar.requested_at
    FROM approval_requests ar
    WHERE ar.document_type = 'indent'
      AND ar.document_id IN (68, 69, 70)
    ORDER BY ar.document_id, ar.id
""")
ars = c.fetchall()
for row in ars:
    print(f"  AR #{row[0]}: doc_id={row[1]}, status={row[3]}, total_levels={row[5]}, workflow_id={row[6]}")

# Check the workflows
wf_ids = list(set([str(row[6]) for row in ars]))
print(f"\n=== Workflows {','.join(wf_ids)} ===")
c.execute(f"""
    SELECT id, name, module, document_type, project_id, is_active 
    FROM approval_workflows WHERE id IN ({','.join(wf_ids)})
""")
for row in c.fetchall():
    print(f"  WF #{row[0]}: name='{row[1]}', project_id={row[4]}, is_active={row[5]}")

# Check indents themselves
print("\n=== Indents 68, 69, 70 ===")
c.execute("""
    SELECT i.id, i.indent_number, i.status, i.raised_by, 
           i.project_id, i.warehouse_id
    FROM indents i
    WHERE i.id IN (68, 69, 70)
    ORDER BY i.id
""")
for row in c.fetchall():
    print(f"  Indent #{row[0]}: number='{row[1]}', status='{row[2]}', raised_by={row[3]}, project_id={row[4]}, warehouse_id={row[5]}")

# Check if there's an approval_histories table
print("\n=== checking for history table ===")
c.execute("SHOW TABLES LIKE '%approval_histor%'")
tables = c.fetchall()
if tables:
    for t in tables:
        c.execute(f"DESCRIBE {t[0]}")
        print(f"  {t[0]} columns:")
        for col in c.fetchall():
            print(f"    {col[0]} ({col[1]})")
else:
    print("  No approval_histor% table found")
    c.execute("SHOW TABLES LIKE '%histor%'")
    for row in c.fetchall():
        print(f"  Found table: {row[0]}")

# Check what references approval_requests
print("\n=== tables with foreign keys to approval_requests ===")
c.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_NAME = 'approval_requests'
      AND TABLE_SCHEMA = %s
""", (settings.DB_NAME,))
for row in c.fetchall():
    print(f"  {row[0]}.{row[1]} -> {row[2]}.{row[3]}")

conn.close()
