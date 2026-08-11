import sqlite3
from pathlib import Path

db = Path.home() / ".cc-switch" / "cc-switch.db"
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
c = con.cursor()

print("=== by app_type ===")
for row in c.execute(
    """
    SELECT app_type, COUNT(*),
           SUM(COALESCE(input_tokens,0)),
           SUM(COALESCE(output_tokens,0)),
           SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0))
    FROM proxy_request_logs
    GROUP BY app_type
    ORDER BY 5 DESC
    """
):
    print(row)

print("\n=== by provider_id (top) ===")
for row in c.execute(
    """
    SELECT provider_id, COUNT(*),
           SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)) AS s
    FROM proxy_request_logs
    GROUP BY provider_id
    ORDER BY s DESC
    LIMIT 15
    """
):
    print(row)

print("\n=== by provider_type ===")
for row in c.execute(
    """
    SELECT provider_type, COUNT(*),
           SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0))
    FROM proxy_request_logs
    GROUP BY provider_type
    ORDER BY 3 DESC
    """
):
    print(row)

print("\n=== daily rollups recent ===")
for row in c.execute(
    """
    SELECT date, app_type,
           SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0))
    FROM usage_daily_rollups
    GROUP BY date, app_type
    ORDER BY date DESC, 3 DESC
    LIMIT 20
    """
):
    print(row)

print("\n=== all time ===")
print(
    c.execute(
        """
        SELECT SUM(COALESCE(input_tokens,0)),
               SUM(COALESCE(output_tokens,0)),
               SUM(COALESCE(input_tokens,0)+COALESCE(output_tokens,0)),
               SUM(CAST(total_cost_usd AS REAL))
        FROM proxy_request_logs
        """
    ).fetchone()
)
