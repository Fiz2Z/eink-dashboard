import sqlite3
from pathlib import Path

db = Path.home() / ".cc-switch" / "cc-switch.db"
print("db:", db, "exists:", db.is_file(), "size:", db.stat().st_size if db.is_file() else 0)
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cur = con.cursor()
tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("TABLES:", tables)
for t in tables:
    low = t.lower()
    if any(k in low for k in ["usage", "token", "request", "stat", "cost", "log", "metric"]):
        print("\n==", t, "==")
        cols = cur.execute(f"PRAGMA table_info({t})").fetchall()
        print("cols:", [(c[1], c[2]) for c in cols])
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print("count:", n)
            rows = cur.execute(f"SELECT * FROM {t} LIMIT 1").fetchall()
            print("sample1:", rows)
        except Exception as e:
            print("err", e)

# also show all table row counts
print("\n--- row counts ---")
for t in tables:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        if n:
            print(f"{t}: {n}")
    except Exception as e:
        print(t, e)
