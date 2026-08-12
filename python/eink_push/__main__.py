"""
CLI:

  python -m eink_push scan
  python -m eink_push preview
  python -m eink_push push
  python -m eink_push push --config config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from .ble_client import EpdBleClient
from .image_codec import load_and_fit, pack_planes, quantize_bw_red
from .render_token import render_token

log = logging.getLogger("eink_push")


def setup_logging(verbose: bool, log_file: Path | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        # default beside CWD
        cand = Path("config.yaml")
        if not cand.is_file():
            return {}
        path = cand
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise SystemExit("config 必须是 YAML 对象")
    return data


def merge_token_data(cfg: dict[str, Any]) -> dict[str, Any]:
    token = dict(cfg.get("token") or {})
    # normalize keys
    out = {
        "total": token.get("total", 0),
        "limit": token.get("limit", 1),
        "reset_days": token.get("reset_days", token.get("resetDays", 0)),
        "codex": token.get("codex", 0),
        "claude": token.get("claude", 0),
        "grok": token.get("grok", 0),
        "deepseek": token.get("deepseek", 0),
        "date_label": token.get("date_label", token.get("dateLabel", "")),
    }
    return out


async def fetch_api(cfg: dict[str, Any]) -> dict[str, Any]:
    import httpx

    api = cfg.get("api") or {}
    url = api.get("url")
    if not url:
        raise SystemExit("source=api 但未配置 api.url")
    headers = api.get("headers") or {}
    timeout = float(api.get("timeout") or 30)
    log.info("GET %s", url)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, dict):
        raise SystemExit("API 必须返回 JSON 对象")
    # allow nested { "token": {...} }
    if "token" in data and isinstance(data["token"], dict):
        data = {**data, **data["token"]}
    base = merge_token_data(cfg)
    aliases = {
        "reset_days": ["reset_days", "resetDays"],
        "date_label": ["date_label", "dateLabel"],
    }
    for k in list(base.keys()):
        keys = aliases.get(k, [k])
        for key in keys:
            if key in data and data[key] is not None:
                base[k] = data[key]
                break
    return base


async def build_image_async(cfg: dict[str, Any], args: argparse.Namespace):
    disp = cfg.get("display") or {}
    w = int(args.width or disp.get("width") or 400)
    h = int(args.height or disp.get("height") or 300)
    source = (args.source or cfg.get("source") or "demo").lower()

    if source == "image":
        path = args.image or cfg.get("image_path")
        if not path:
            raise SystemExit("source=image 需要 --image 或 config image_path")
        log.info("Load image %s", path)
        return load_and_fit(str(path), w, h)

    if source == "api":
        data = await fetch_api(cfg)
        log.info("Render from API: %s", data)
        return quantize_bw_red(render_token(w, h, data))

    if source in ("cc_switch", "cc-switch", "ccswitch"):
        from .cc_switch import default_db_path, fetch_dashboard_usage

        cs = cfg.get("cc_switch") or {}
        db = cs.get("db_path") or default_db_path()
        include_cache = bool(cs.get("include_cache", False))
        data = fetch_dashboard_usage(Path(db) if db else None, include_cache=include_cache)
        log.info(
            "Render CC Switch 30d panel: total30d=%s today=%s codex=%s grok=%s",
            data.get("total_30d"),
            data.get("today_total"),
            data.get("codex_30d"),
            data.get("grok_30d"),
        )
        # render_token already quantizes to exact BWR
        return render_token(w, h, data)

    if source == "demo":
        # synthetic 30-day demo matching reference proportions
        import random

        random.seed(42)
        daily = [random.randint(20_000, 80_000) for _ in range(29)] + [58_600]
        codex_30d = 986_000
        grok_30d = 496_000
        total_30d = codex_30d + grok_30d
        data = {
            "total_30d": total_30d,
            "today_total": 58_600,
            "codex_30d": codex_30d,
            "grok_30d": grok_30d,
            "codex_pct": round(codex_30d / total_30d * 100),
            "grok_pct": 100 - round(codex_30d / total_30d * 100),
            "daily": daily,
            "start_label": "JUL 14",
            "end_label": "AUG 12",
        }
        log.info("Render demo 30d token panel")
        return render_token(w, h, data)

    data = merge_token_data(cfg)
    # legacy flat fields → minimal dashboard
    data = {
        "total_30d": data.get("total") or 0,
        "today_total": data.get("total") or 0,
        "codex_30d": data.get("codex") or 0,
        "grok_30d": data.get("grok") or 0,
        "codex_pct": 50,
        "grok_pct": 50,
        "daily": [0] * 30,
        "start_label": "",
        "end_label": data.get("date_label") or "",
    }
    t = (data["codex_30d"] or 0) + (data["grok_30d"] or 0)
    if t > 0:
        data["codex_pct"] = round(data["codex_30d"] / t * 100)
        data["grok_pct"] = 100 - data["codex_pct"]
    log.info("Render legacy token dashboard %sx%s", w, h)
    return render_token(w, h, data)


async def cmd_scan(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    ble = cfg.get("ble") or {}
    client = EpdBleClient()
    await client.scan(
        timeout=float(args.timeout or ble.get("scan_timeout") or 20),
        name_prefix=str(
            args.name_prefix or ble.get("name_prefix") or ble.get("device_name") or "NRF_EPD"
        ),
        show_all=bool(args.all),
    )


async def cmd_preview(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    img = await build_image_async(cfg, args)
    out = Path(args.out or cfg.get("save_preview") or "preview.png")
    img.save(out)
    log.info("Saved preview → %s", out.resolve())


async def cmd_push(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    ble = cfg.get("ble") or {}
    disp = cfg.get("display") or {}
    retry_cfg = cfg.get("retry") or {}

    # Whole-job retries (connect + full transfer)
    job_retries = int(
        args.job_retries
        if getattr(args, "job_retries", None) is not None
        else retry_cfg.get("job_retries", 3)
    )
    job_delay = float(retry_cfg.get("job_retry_delay_sec", 15))
    connect_retries = int(ble.get("connect_retries") or 5)

    img = await build_image_async(cfg, args)

    preview = args.out or cfg.get("save_preview")
    if preview:
        Path(preview).parent.mkdir(parents=True, exist_ok=True)
        img.save(preview)
        log.info("Preview → %s", preview)

    color_mode = (args.color_mode or disp.get("color_mode") or "threeColor").lower()
    use_red_content = color_mode in ("threecolor", "three_color", "bwr")

    if use_red_content:
        bw, red = pack_planes(img)
        log.info("Packed BWR content: bw=%s red=%s (real red channel)", len(bw), len(red))
    else:
        gray = img.convert("L")
        mono = gray.point(lambda p: 0 if p < 160 else 255, mode="L").convert("RGB")
        bw, _ignored = pack_planes(mono)
        red = bytes([0xFF] * len(bw))
        log.info(
            "Packed BW content + white red plane: bw=%s red=%s (clears red dots)",
            len(bw),
            len(red),
        )

    address = (args.address or ble.get("address") or None) or None
    if address == "":
        address = None
    name_prefix = str(
        args.name_prefix or ble.get("name_prefix") or ble.get("device_name") or "NRF_EPD"
    )
    scan_timeout = float(args.timeout or ble.get("scan_timeout") or 20)
    interleaved = int(args.interleaved if args.interleaved is not None else 0)
    chunk_delay = float(args.chunk_delay if args.chunk_delay is not None else 0.012)
    settle = float(args.settle if args.settle is not None else 18.0)

    last_err: Exception | None = None
    for job in range(1, job_retries + 1):
        client = EpdBleClient()
        try:
            log.info("=== Push job %s/%s ===", job, job_retries)
            # Attempt 1: configured address; on fail fall back to name scan
            try:
                await client.connect(
                    address=address,
                    name_prefix=name_prefix,
                    timeout=scan_timeout,
                    retries=connect_retries,
                )
            except Exception as e:
                if address:
                    log.warning(
                        "Connect by address failed (%s); retry by name %r …",
                        e,
                        name_prefix,
                    )
                    await client.disconnect()
                    await client.connect(
                        address=None,
                        name_prefix=name_prefix,
                        timeout=scan_timeout,
                        retries=connect_retries,
                    )
                else:
                    raise

            def progress(i: int, total: int, plane: str) -> None:
                log.info("  %s %s/%s", plane, i, total)

            await client.push_planes(
                bw,
                red,
                three_color=True,
                interleaved=interleaved,
                chunk_delay=chunk_delay,
                settle_after_refresh=settle,
                on_progress=progress,
            )
            log.info("推送成功 (job %s/%s)。", job, job_retries)
            return
        except Exception as e:
            last_err = e
            log.error("推送失败 (job %s/%s): %s", job, job_retries, e)
            if job < job_retries:
                log.info("%.0f 秒后整任务重试…", job_delay)
                await asyncio.sleep(job_delay)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    raise SystemExit(f"推送在 {job_retries} 次整任务重试后仍失败: {last_err}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eink_push",
        description="Push images to EPD-nRF5 e-ink panels via BLE (bleak + Pillow)",
    )
    p.add_argument("-c", "--config", type=Path, help="config.yaml path")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="also write logs to this file (for silent/pythonw runs)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="Scan BLE devices")
    s.add_argument("--timeout", type=float, default=None)
    s.add_argument("--name-prefix", default=None, help="e.g. NRF_EPD_459F")
    s.add_argument(
        "--all",
        action="store_true",
        help="also print non-matching devices",
    )

    s = sub.add_parser("preview", help="Render image only (no BLE)")
    s.add_argument(
        "--source",
        choices=["demo", "api", "image", "cc_switch"],
        default=None,
    )
    s.add_argument("--image", default=None)
    s.add_argument("--width", type=int, default=None)
    s.add_argument("--height", type=int, default=None)
    s.add_argument("--out", default="preview.png")

    s = sub.add_parser("push", help="Render + BLE push")
    s.add_argument(
        "--source",
        choices=["demo", "api", "image", "cc_switch"],
        default=None,
    )
    s.add_argument("--image", default=None)
    s.add_argument("--width", type=int, default=None)
    s.add_argument("--height", type=int, default=None)
    s.add_argument("--out", default=None, help="optional preview path")
    s.add_argument("--address", default=None)
    s.add_argument("--name-prefix", default=None)
    s.add_argument("--timeout", type=float, default=None)
    s.add_argument("--color-mode", choices=["threeColor", "bw"], default=None)
    s.add_argument("--interleaved", type=int, default=None)
    s.add_argument(
        "--chunk-delay",
        type=float,
        default=None,
        help="seconds between BLE chunks (default 0.012)",
    )
    s.add_argument(
        "--settle",
        type=float,
        default=None,
        help="seconds to wait after REFRESH for e-ink full refresh (default 18)",
    )
    s.add_argument(
        "--job-retries",
        type=int,
        default=None,
        help="full connect+push retries on failure (default 3)",
    )

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose, getattr(args, "log_file", None))
    cfg = load_config(args.config)

    if args.cmd == "scan":
        asyncio.run(cmd_scan(args, cfg))
    elif args.cmd == "preview":
        asyncio.run(cmd_preview(args, cfg))
    elif args.cmd == "push":
        asyncio.run(cmd_push(args, cfg))
    else:
        parser.error("unknown command")


if __name__ == "__main__":
    main()
