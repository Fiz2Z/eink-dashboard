"""
Read today's token usage from CC Switch local SQLite DB.

Default path: ~/.cc-switch/cc-switch.db
Tables: proxy_request_logs (detail), usage_daily_rollups (daily)

"Today" = local calendar day of the machine running this script.
Tokens = input_tokens + output_tokens (cache tokens not included by default).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("eink_push.cc_switch")

# Map CC Switch app_type / provider_type → dashboard bucket
# Unmatched usage goes into "other" (counted in total only).
APP_BUCKETS = {
    "codex": "codex",
    "codex_session": "codex",
    "claude": "claude",
    "claude_session": "claude",
    "grok": "grok",
    "grokbuild": "grok",
    "grok_session": "grok",
    "grokbuild_session": "grok",
    "deepseek": "deepseek",
    "openai": "codex",  # often codex/openai family
}


def default_db_path() -> Path:
    return Path.home() / ".cc-switch" / "cc-switch.db"


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"CC Switch DB not found: {db_path}")
    # Read-only URI so we never lock/write the live app DB
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5.0)


def _bucket_for(app_type: str | None, provider_type: str | None, provider_id: str | None) -> str:
    for key in (app_type, provider_type, provider_id):
        if not key:
            continue
        k = str(key).strip().lower()
        if k in APP_BUCKETS:
            return APP_BUCKETS[k]
        # fuzzy
        if "codex" in k or "openai" in k or "gpt" in k:
            return "codex"
        if "claude" in k or "anthropic" in k:
            return "claude"
        if "grok" in k or "xai" in k:
            return "grok"
        if "deepseek" in k:
            return "deepseek"
    return "other"


def fetch_today_usage(
    db_path: Path | None = None,
    *,
    include_cache: bool = False,
    day: str | None = None,
) -> dict[str, Any]:
    """
    Aggregate today's tokens from proxy_request_logs.

    created_at is unix seconds (see inspect samples).

    Returns dict compatible with render_token / merge_token_data:
      total, codex, claude, grok, deepseek, date_label, ...
    """
    path = Path(db_path) if db_path else default_db_path()
    day = day or datetime.now().strftime("%Y-%m-%d")
    # local day bounds
    start = datetime.strptime(day, "%Y-%m-%d")
    end = start.replace(hour=23, minute=59, second=59)
    # if system uses naive local time for created_at (samples look like epoch)
    t0 = int(start.timestamp())
    t1 = int(end.timestamp()) + 1

    token_expr = (
        "COALESCE(input_tokens,0)+COALESCE(output_tokens,0)"
        "+COALESCE(cache_read_tokens,0)+COALESCE(cache_creation_tokens,0)"
        if include_cache
        else "COALESCE(input_tokens,0)+COALESCE(output_tokens,0)"
    )

    buckets = {"codex": 0, "claude": 0, "grok": 0, "deepseek": 0, "other": 0}
    requests = 0
    cost = 0.0

    con = _connect_ro(path)
    try:
        cur = con.cursor()
        # Prefer detail logs for "today"
        rows = cur.execute(
            f"""
            SELECT app_type, provider_type, provider_id,
                   {token_expr} AS tok,
                   COALESCE(total_cost_usd, '0')
            FROM proxy_request_logs
            WHERE created_at >= ? AND created_at < ?
            """,
            (t0, t1),
        ).fetchall()

        if not rows:
            # fallback: daily rollups for this date (may lag)
            log.warning(
                "No proxy_request_logs for %s; trying usage_daily_rollups", day
            )
            rows2 = cur.execute(
                f"""
                SELECT app_type, '', provider_id,
                       COALESCE(input_tokens,0)+COALESCE(output_tokens,0)
                       {("+COALESCE(cache_read_tokens,0)+COALESCE(cache_creation_tokens,0)" if include_cache else "")}
                       AS tok,
                       COALESCE(total_cost_usd, '0')
                FROM usage_daily_rollups
                WHERE date = ?
                """,
                (day,),
            ).fetchall()
            rows = rows2

        for app_type, provider_type, provider_id, tok, cost_s in rows:
            requests += 1
            tok_i = int(tok or 0)
            b = _bucket_for(app_type, provider_type, provider_id)
            buckets[b] = buckets.get(b, 0) + tok_i
            try:
                cost += float(cost_s or 0)
            except (TypeError, ValueError):
                pass
    finally:
        con.close()

    total = sum(buckets.values())
    # date label like AUG 11
    d = datetime.strptime(day, "%Y-%m-%d")
    months = [
        "JAN",
        "FEB",
        "MAR",
        "APR",
        "MAY",
        "JUN",
        "JUL",
        "AUG",
        "SEP",
        "OCT",
        "NOV",
        "DEC",
    ]
    date_label = f"{months[d.month - 1]} {d.day}"

    log.info(
        "CC Switch %s: total=%s codex=%s claude=%s grok=%s deepseek=%s other=%s req=%s cost=$%.4f db=%s",
        day,
        total,
        buckets["codex"],
        buckets["claude"],
        buckets["grok"],
        buckets["deepseek"],
        buckets["other"],
        requests,
        cost,
        path,
    )

    return {
        "total": total,
        "codex": buckets["codex"],
        "claude": buckets["claude"],
        "grok": buckets["grok"],
        "deepseek": buckets["deepseek"],
        "other": buckets["other"],
        "date_label": date_label,
        "reset_days": 0,
        # keep limit from config merge; placeholder
        "limit": None,
        "cost_usd": round(cost, 4),
        "request_count": requests,
        "day": day,
    }
