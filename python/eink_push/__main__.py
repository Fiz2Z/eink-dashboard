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


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


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

    data = merge_token_data(cfg)
    log.info("Render demo token dashboard %sx%s", w, h)
    return quantize_bw_red(render_token(w, h, data))


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
    img = await build_image_async(cfg, args)

    preview = args.out or cfg.get("save_preview")
    if preview:
        Path(preview).parent.mkdir(parents=True, exist_ok=True)
        img.save(preview)
        log.info("Preview → %s", preview)

    bw, red = pack_planes(img)
    three = (args.color_mode or disp.get("color_mode") or "threeColor") != "bw"
    log.info("Packed bw=%s red=%s three_color=%s", len(bw), len(red), three)

    client = EpdBleClient()
    try:
        await client.connect(
            address=(args.address or ble.get("address") or None) or None,
            name_prefix=str(
                args.name_prefix
                or ble.get("name_prefix")
                or ble.get("device_name")
                or "NRF_EPD"
            ),
            timeout=float(args.timeout or ble.get("scan_timeout") or 20),
            retries=int(ble.get("connect_retries") or 5),
        )

        def progress(i: int, total: int, plane: str) -> None:
            log.info("  %s %s/%s", plane, i, total)

        await client.push_planes(
            bw,
            red if three else None,
            three_color=three,
            interleaved=int(args.interleaved if args.interleaved is not None else 0),
            on_progress=progress,
        )
        log.info("Done. Wait for full refresh; BLE may drop (normal).")
        await asyncio.sleep(2)
    finally:
        await client.disconnect()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eink_push",
        description="Push images to EPD-nRF5 e-ink panels via BLE (bleak + Pillow)",
    )
    p.add_argument("-c", "--config", type=Path, help="config.yaml path")
    p.add_argument("-v", "--verbose", action="store_true")
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
    s.add_argument("--source", choices=["demo", "api", "image"], default=None)
    s.add_argument("--image", default=None)
    s.add_argument("--width", type=int, default=None)
    s.add_argument("--height", type=int, default=None)
    s.add_argument("--out", default="preview.png")

    s = sub.add_parser("push", help="Render + BLE push")
    s.add_argument("--source", choices=["demo", "api", "image"], default=None)
    s.add_argument("--image", default=None)
    s.add_argument("--width", type=int, default=None)
    s.add_argument("--height", type=int, default=None)
    s.add_argument("--out", default=None, help="optional preview path")
    s.add_argument("--address", default=None)
    s.add_argument("--name-prefix", default=None)
    s.add_argument("--timeout", type=float, default=None)
    s.add_argument("--color-mode", choices=["threeColor", "bw"], default=None)
    s.add_argument("--interleaved", type=int, default=None)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)
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
