"""Simple multi-provider token dashboard for e-ink (Pillow)."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

RED = (230, 0, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
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

# Map provider key -> icon stem (assets/icons/{stem}.png)
ICON_STEM = {
    "CODEX": "openai",
    "CLAUDE": "anthropic",
    "GROK": "grok",
    "DEEPSEEK": "deepseek",
}


def _icon_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    # python/eink_push/render_token.py -> repo root assets/icons
    repo_icons = here.parents[2] / "assets" / "icons"
    local = here.parents[1] / "assets" / "icons"
    cwd = Path.cwd() / "assets" / "icons"
    cwd2 = Path.cwd().parent / "assets" / "icons"
    return [repo_icons, local, cwd, cwd2]


@lru_cache(maxsize=8)
def load_icon(stem: str, size: int) -> Image.Image | None:
    """Load PNG (preferred) or fail gracefully."""
    for d in _icon_dirs():
        for ext in (".png", ".PNG"):
            p = d / f"{stem}{ext}"
            if p.is_file():
                im = Image.open(p).convert("RGBA")
                im = im.resize((size, size), Image.Resampling.LANCZOS)
                return _to_black_alpha(im)
    return None


def _to_black_alpha(im: Image.Image) -> Image.Image:
    """Any opaque pixel -> black (e-ink friendly)."""
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                px[x, y] = (0, 0, 0, 0)
            else:
                # dark enough or any non-white → black mark
                if r < 250 or g < 250 or b < 250:
                    px[x, y] = (0, 0, 0, a)
                else:
                    px[x, y] = (0, 0, 0, 0)
    return im


def _paste_icon(base: Image.Image, icon: Image.Image, xy: tuple[int, int]) -> None:
    base.paste(icon, xy, icon)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    windir = Path(r"C:\Windows\Fonts")
    if windir.is_dir():
        candidates += [
            windir / "msyhbd.ttc",
            windir / "msyh.ttc",
            windir / "arialbd.ttf",
            windir / "arial.ttf",
            windir / "simhei.ttf",
        ]
    candidates += [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _num(v: Any) -> float:
    try:
        return float(str(v).replace(",", "").replace("_", "").strip())
    except (TypeError, ValueError):
        return 0.0


def format_compact(n: float) -> str:
    n = abs(float(n))
    if n >= 1e9:
        x = n / 1e9
        return f"{x:.2f}".rstrip("0").rstrip(".") + "B"
    if n >= 1e6:
        x = n / 1e6
        return f"{x:.2f}".rstrip("0").rstrip(".") + "M"
    if n >= 1e3:
        x = n / 1e3
        return f"{x:.2f}".rstrip("0").rstrip(".") + "K"
    return str(int(round(n)))


def render_token(width: int, height: int, data: dict[str, Any]) -> Image.Image:
    """
    data keys: total, limit, reset_days, codex, claude, grok, deepseek, date_label?
    """
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    s = min(width / 400, height / 300)

    total = _num(data.get("total", 0))
    limit = max(1.0, _num(data.get("limit", 1)))
    total_pct = min(100, round(total / limit * 100))
    providers = [
        ("CODEX", _num(data.get("codex", 0))),
        ("CLAUDE", _num(data.get("claude", 0))),
        ("GROK", _num(data.get("grok", 0))),
        ("DEEPSEEK", _num(data.get("deepseek", 0))),
    ]
    psum = sum(v for _, v in providers) or 1.0
    providers = [(n, v, round(v / psum * 100)) for n, v in providers]

    m = max(4, round(6 * s))
    header_h = max(28, round(36 * s))
    gap = max(4, round(6 * s))
    border = max(2, round(3 * s))

    # Header
    draw.rectangle([0, 0, width, header_h], fill=BLACK)
    f_h = _font(max(14, round(18 * s)))
    draw.text((m + 2, header_h // 2), "AI TOKEN", fill=WHITE, font=f_h, anchor="lm")
    date_label = str(data.get("date_label") or "").strip()
    if not date_label:
        now = datetime.now()
        date_label = f"{MONTHS[now.month - 1]} {now.day}"
    draw.text(
        (width - m - 2, header_h // 2),
        date_label,
        fill=WHITE,
        font=f_h,
        anchor="rm",
    )

    # Outer frame (no footer strip)
    body_top = header_h
    body_bot = height
    draw.rectangle(
        [m, body_top + m, width - m, body_bot - m],
        outline=BLACK,
        width=border,
    )

    # TOTAL card
    total_y = body_top + m + gap
    total_h = max(48, round(62 * s))
    total_x = m + gap
    total_w = width - m * 2 - gap * 2
    draw.rectangle(
        [total_x, total_y, total_x + total_w, total_y + total_h],
        outline=BLACK,
        width=border,
    )
    f_label = _font(max(14, round(18 * s)))
    f_big = _font(max(28, round(40 * s)))
    ty = total_y + total_h // 2
    draw.text((total_x + round(10 * s), ty), "TOTAL", fill=BLACK, font=f_label, anchor="lm")
    total_text = format_compact(total)
    badge_w = max(52, round(64 * s))
    badge_h = max(28, round(36 * s))
    badge_x = total_x + total_w - round(8 * s) - badge_w
    badge_y = total_y + (total_h - badge_h) // 2
    num_x = total_x + round(10 * s) + round(78 * s)
    draw.text((num_x, ty), total_text, fill=BLACK, font=f_big, anchor="lm")

    _rounded_rect(draw, badge_x, badge_y, badge_w, badge_h, max(4, round(6 * s)), RED)
    f_badge = _font(max(16, round(22 * s)))
    draw.text(
        (badge_x + badge_w // 2, badge_y + badge_h // 2),
        f"{total_pct}%",
        fill=WHITE,
        font=f_badge,
        anchor="mm",
    )

    # 2x2 cards
    grid_top = total_y + total_h + gap
    grid_bot = body_bot - m - gap
    grid_left = total_x
    grid_w = total_w
    grid_h = grid_bot - grid_top
    cell_w = (grid_w - gap) / 2
    cell_h = (grid_h - gap) / 2
    positions = [
        (grid_left, grid_top),
        (grid_left + cell_w + gap, grid_top),
        (grid_left, grid_top + cell_h + gap),
        (grid_left + cell_w + gap, grid_top + cell_h + gap),
    ]
    f_pct = _font(max(13, round(16 * s)))
    f_val = _font(max(18, round(22 * s)))
    # larger icon when vendor name is omitted
    icon_size = max(28, round(36 * s))

    for (name, val, pct), (cx, cy) in zip(providers, positions):
        x0, y0 = int(cx), int(cy)
        x1, y1 = int(cx + cell_w), int(cy + cell_h)
        draw.rectangle([x0, y0, x1, y1], outline=BLACK, width=border)
        pad = max(6, round(8 * s))

        # icon only (no CODEX/GROK/… labels) — same assets as web
        stem = ICON_STEM.get(name, "")
        icon = load_icon(stem, icon_size) if stem else None
        text_x = x0 + pad
        if icon is not None:
            _paste_icon(img, icon, (x0 + pad, y0 + pad + round(2 * s)))
            text_x = x0 + pad + icon_size + round(8 * s)

        # usage number + percent only
        draw.text(
            (text_x, y0 + pad + round(4 * s)),
            format_compact(val),
            fill=BLACK,
            font=f_val,
        )
        pct_s = f"{pct}%"
        tw = draw.textlength(pct_s, font=f_pct)
        draw.text(
            (x1 - pad - tw, y0 + pad + round(8 * s)),
            pct_s,
            fill=BLACK,
            font=f_pct,
        )
        bar_x = x0 + pad
        bar_w = (x1 - x0) - pad * 2
        bar_h = max(8, round(10 * s))
        bar_y = y1 - pad - bar_h
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=BLACK, width=2)
        fill_w = int(bar_w * min(100, pct) / 100)
        if fill_w > 2:
            inset = 2
            draw.rectangle(
                [
                    bar_x + inset,
                    bar_y + inset,
                    bar_x + max(inset, fill_w - inset),
                    bar_y + bar_h - inset,
                ],
                fill=RED,
            )

    return img


def _rounded_rect(draw: ImageDraw.ImageDraw, x, y, w, h, r, fill):
    try:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)
    except Exception:
        draw.rectangle([x, y, x + w, y + h], fill=fill)
