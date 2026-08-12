"""
Read token usage from CC Switch local SQLite DB.

Default path: ~/.cc-switch/cc-switch.db

Dashboard fields (Codex + Grok only):
  - last 30 calendar days daily series
  - 30d totals per provider
  - today totals
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger("eink_push.cc_switch")

MONTHS = [
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
    "openai": "codex",
}


def default_db_path() -> Path:
    return Path.home() / ".cc-switch" / "cc-switch.db"


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise FileNotFoundError(f"CC Switch DB not found: {db_path}")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=5.0)


def _bucket_for(app_type: str | None, provider_type: str | None, provider_id: str | None) -> str:
    for key in (app_type, provider_type, provider_id):
        if not key:
            continue
        k = str(key).strip().lower()
        if k in APP_BUCKETS:
            return APP_BUCKETS[k]
        if "codex" in k or "openai" in k or "gpt" in k:
            return "codex"
        if "claude" in k or "anthropic" in k:
            return "claude"
        if "grok" in k or "xai" in k:
            return "grok"
        if "deepseek" in k:
            return "deepseek"
    return "other"


def _token_expr(include_cache: bool) -> str:
    if include_cache:
        return (
            "COALESCE(input_tokens,0)+COALESCE(output_tokens,0)"
            "+COALESCE(cache_read_tokens,0)+COALESCE(cache_creation_tokens,0)"
        )
    return "COALESCE(input_tokens,0)+COALESCE(output_tokens,0)"


def _date_label(d: datetime) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def fetch_dashboard_usage(
    db_path: Path | None = None,
    *,
    include_cache: bool = False,
    end_day: str | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """
    Build dashboard data for Codex + Grok only.

    Returns:
      total_30d, today_total,
      codex_30d, grok_30d,
      daily: list[int] length=days (oldest → today),
      start_label, end_label (e.g. JUL 14 / AUG 12),
      codex_pct, grok_pct,
    """
    path = Path(db_path) if db_path else default_db_path()
    end = datetime.strptime(end_day or datetime.now().strftime("%Y-%m-%d"), "%Y-%m-%d")
    start = end - timedelta(days=days - 1)

    # day keys oldest → newest
    day_list = [start + timedelta(days=i) for i in range(days)]
    day_keys = [d.strftime("%Y-%m-%d") for d in day_list]

    # per day codex+grok totals, and 30d per vendor
    daily_cg = {k: 0 for k in day_keys}
    codex_30d = 0
    grok_30d = 0
    codex_today = 0
    grok_today = 0

    t0 = int(start.timestamp())
    t1 = int(end.replace(hour=23, minute=59, second=59).timestamp()) + 1
    expr = _token_expr(include_cache)
    today_key = day_keys[-1]

    con = _connect_ro(path)
    try:
        cur = con.cursor()
        rows = cur.execute(
            f"""
            SELECT created_at, app_type, provider_type, provider_id, {expr} AS tok
            FROM proxy_request_logs
            WHERE created_at >= ? AND created_at < ?
            """,
            (t0, t1),
        ).fetchall()

        used_logs = bool(rows)
        if not rows:
            log.warning("No proxy_request_logs in window; trying usage_daily_rollups")
            # rollups by date string
            rows_r = cur.execute(
                f"""
                SELECT date, app_type, '', provider_id,
                       COALESCE(input_tokens,0)+COALESCE(output_tokens,0)
                       {("+COALESCE(cache_read_tokens,0)+COALESCE(cache_creation_tokens,0)" if include_cache else "")}
                FROM usage_daily_rollups
                WHERE date >= ? AND date <= ?
                """,
                (day_keys[0], day_keys[-1]),
            ).fetchall()
            for date_s, app_type, _pt, provider_id, tok in rows_r:
                b = _bucket_for(app_type, None, provider_id)
                if b not in ("codex", "grok"):
                    continue
                tok_i = int(tok or 0)
                if date_s in daily_cg:
                    daily_cg[date_s] += tok_i
                if b == "codex":
                    codex_30d += tok_i
                    if date_s == today_key:
                        codex_today += tok_i
                else:
                    grok_30d += tok_i
                    if date_s == today_key:
                        grok_today += tok_i
        else:
            for created_at, app_type, provider_type, provider_id, tok in rows:
                b = _bucket_for(app_type, provider_type, provider_id)
                if b not in ("codex", "grok"):
                    continue
                tok_i = int(tok or 0)
                try:
                    day_s = datetime.fromtimestamp(int(created_at)).strftime("%Y-%m-%d")
                except (TypeError, ValueError, OSError):
                    continue
                if day_s in daily_cg:
                    daily_cg[day_s] += tok_i
                if b == "codex":
                    codex_30d += tok_i
                    if day_s == today_key:
                        codex_today += tok_i
                else:
                    grok_30d += tok_i
                    if day_s == today_key:
                        grok_today += tok_i

        _ = used_logs
    finally:
        con.close()

    daily = [daily_cg[k] for k in day_keys]
    total_30d = codex_30d + grok_30d
    today_total = codex_today + grok_today

    if total_30d > 0:
        codex_pct = round(codex_30d / total_30d * 100)
        grok_pct = 100 - codex_pct
    else:
        codex_pct = 0
        grok_pct = 0

    log.info(
        "CC Switch %s days ending %s: 30d=%s today=%s codex30d=%s grok30d=%s pct=%s/%s db=%s",
        days,
        today_key,
        total_30d,
        today_total,
        codex_30d,
        grok_30d,
        codex_pct,
        grok_pct,
        path,
    )

    return {
        "total_30d": total_30d,
        "today_total": today_total,
        "codex_30d": codex_30d,
        "grok_30d": grok_30d,
        "codex_today": codex_today,
        "grok_today": grok_today,
        "codex_pct": codex_pct,
        "grok_pct": grok_pct,
        "daily": daily,
        "start_label": _date_label(start),
        "end_label": _date_label(end),
        "day": today_key,
        # legacy keys for older callers
        "total": today_total,
        "codex": codex_30d,
        "grok": grok_30d,
        "date_label": _date_label(end),
    }


def fetch_today_usage(
    db_path: Path | None = None,
    *,
    include_cache: bool = False,
    day: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible: today-only view fields from full dashboard query. """
    data = fetch_dashboard_usage(db_path, include_cache=include_cache, end_day=day, days=30)
    return {
        "total": data["today_total"],
        "codex": data["codex_today"],
        "claude": 0,
        "grok": data["grok_today"],
        "deepseek": 0,
        "other": 0,
        "date_label": data["end_label"],
        "reset_days": 0,
        "limit": None,
        "day": data["day"],
        **data,
    }
