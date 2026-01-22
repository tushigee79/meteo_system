import sqlite3

c = sqlite3.connect("db_work.sqlite3", timeout=30)
cur = c.cursor()

cur.execute("PRAGMA journal_mode=DELETE;")

# 1) JSON биш бүх утгыг [] болгоно (NOT NULL-д safe)
cur.execute("""
UPDATE inventory_devicesystemprofile
SET subsystems = '[]'
WHERE subsystems IS NULL
   OR subsystems IN ('', 'null', 'None')
   OR json_valid(subsystems) = 0
""")

c.commit()
print("fixed rows:", cur.rowcount)
c.close()
