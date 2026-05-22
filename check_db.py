import sqlite3

conn = sqlite3.connect("results/guardian.db")
conn.row_factory = sqlite3.Row

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t["name"] for t in tables])

rows = conn.execute("SELECT alert_status, COUNT(*) as cnt FROM Alerts GROUP BY alert_status").fetchall()
print("Alert statuses:", [(r["alert_status"], r["cnt"]) for r in rows])

total = conn.execute("SELECT COUNT(*) FROM Alerts").fetchone()[0]
print("Total alerts:", total)

sample = conn.execute("SELECT id, alert_status, reason_code, inserted_at FROM Alerts LIMIT 5").fetchall()
for r in sample:
    print(dict(r))

op = conn.execute("SELECT COUNT(*) FROM Operator_Actions").fetchone()[0]
print("Operator actions:", op)

conn.close()
