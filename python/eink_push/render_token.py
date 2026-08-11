"""Token dashboard renderer — layout matches the TOTAL USED reference card."""

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

ICON_STEM = {
    "CODEX": "openai",
    "CLAUDE": "anthropic",
    "GROK": "grok",
    "DEEPSEEK": "deepseek",
}


def _icon_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parents[2] / "assets" / "icons",
        here.parents[1] / "assets" / "icons",
        Path.cwd() / "assets" / "icons",
        Path.cwd().parent / "assets" / "icons",
    ]


@lru_cache(maxsize=8)
def load_icon(stem: str, size: int) -> Image.Image | None:
    for d in _icon_dirs():
        p = d / f"{stem}.png"
        if p.is_file():
            im = Image.open(p).convert("RGBA")
            im = im.resize((size, size), Image.Resampling.LANCZOS)
            return _to_black_alpha(im)
    return None


def _to_black_alpha(im: Image.Image) -> Image.Image:
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                px[x, y] = (0, 0, 0, 0)
            elif r < 250 or g < 250 or b < 250:
                px[x, y] = (0, 0, 0, a)
            else:
                px[x, y] = (0, 0, 0, 0)
    return im


def _paste_icon(base: Image.Image, icon: Image.Image, xy: tuple[int, int]) -> None:
    base.paste(icon, xy, icon)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


def _round_rect(draw: ImageDraw.ImageDraw, box, radius: int, **kwargs) -> None:
    try:
        draw.rounded_rectangle(box, radius=radius, **kwargs)
    except Exception:
        draw.rectangle(box, **kwargs)


def render_token(width: int, height: int, data: dict[str, Any]) -> Image.Image:
    """
    Layout (reference):
      - black header: AI TOKEN | date
      - TOTAL USED card with huge centered number + short red underline
      - 2×2 cards: icon | value | pct%  + red progress bar
      - no LIMIT/RESET footer, no vendor name text
    """
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)
    s = min(width / 400.0, height / 300.0)

    total = _num(data.get("total", 0))
    limit = max(1.0, _num(data.get("limit", 1)))
    providers = [
        ("CODEX", _num(data.get("codex", 0))),
        ("CLAUDE", _num(data.get("claude", 0))),
        ("GROK", _num(data.get("grok", 0))),
        ("DEEPSEEK", _num(data.get("deepseek", 0))),
    ]
    psum = sum(v for _, v in providers) or 1.0
    providers = [(n, v, round(v / psum * 100)) for n, v in providers]

    m = max(6, round(8 * s))
    header_h = max(30, round(38 * s))
    gap = max(5, round(7 * s))
    radius = max(6, round(8 * s))
    border = max(2, round(2.5 * s))

    # —— Header ——
    draw.rectangle([0, 0, width, header_h], fill=BLACK)
    f_head = _font(max(15, round(18 * s)))
    draw.text((m, header_h // 2), "AI TOKEN", fill=WHITE, font=f_head, anchor="lm")
    date_label = str(data.get("date_label") or "").strip()
    if not date_label:
        now = datetime.now()
        date_label = f"{MONTHS[now.month - 1]} {now.day}"
    draw.text(
        (width - m, header_h // 2), date_label, fill=WHITE, font=f_head, anchor="rm"
    )

    # —— TOTAL USED card ——
    total_x0 = m
    total_y0 = header_h + gap
    total_x1 = width - m
    total_h = max(72, round(88 * s))
    total_y1 = total_y0 + total_h
    _round_rect(
        draw,
        [total_x0, total_y0, total_x1, total_y1],
        radius,
        outline=BLACK,
        width=border,
    )

    f_total_label = _font(max(13, round(15 * s)))
    draw.text(
        (total_x0 + round(12 * s), total_y0 + round(10 * s)),
        "TOTAL USED",
        fill=BLACK,
        font=f_total_label,
        anchor="lt",
    )

    total_text = format_compact(total)
    f_huge = _font(max(40, round(52 * s)))
    cx = (total_x0 + total_x1) // 2
    cy = total_y0 + total_h // 2 + round(6 * s)
    draw.text((cx, cy), total_text, fill=BLACK, font=f_huge, anchor="mm")

    # short red underline under number
    tw = draw.textlength(total_text, font=f_huge)
    ul_w = max(28, int(tw * 0.28))
    ul_h = max(3, round(4 * s))
    ul_y = cy + round(f_huge.size * 0.42) if hasattr(f_huge, "size") else cy + round(22 * s)
    # approximate descender space
    ul_y = cy + max(18, round(26 * s))
    draw.rectangle(
        [cx - ul_w // 2, ul_y, cx + ul_w // 2, ul_y + ul_h],
        fill=RED,
    )

    # —— 2×2 provider cards ——
    grid_top = total_y1 + gap
    grid_bot = height - m
    grid_left = m
    grid_right = width - m
    grid_w = grid_right - grid_left
    grid_h = grid_bot - grid_top
    cell_w = (grid_w - gap) / 2
    cell_h = (grid_h - gap) / 2

    cells = [
        (grid_left, grid_top),
        (grid_left + cell_w + gap, grid_top),
        (grid_left, grid_top + cell_h + gap),
        (grid_left + cell_w + gap, grid_top + cell_h + gap),
    ]

    f_val = _font(max(20, round(26 * s)))
    f_pct = _font(max(13, round(15 * s)))
    icon_size = max(30, round(38 * s))

    for (name, val, pct), (cx0, cy0) in zip(providers, cells):
        x0, y0 = int(cx0), int(cy0)
        x1, y1 = int(cx0 + cell_w), int(cy0 + cell_h)
        _round_rect(draw, [x0, y0, x1, y1], radius, outline=BLACK, width=border)

        pad = max(8, round(10 * s))
        # vertical center content above progress bar
        bar_h = max(8, round(10 * s))
        bar_y = y1 - pad - bar_h
        content_mid_y = (y0 + bar_y) // 2

        stem = ICON_STEM.get(name, "")
        icon = load_icon(stem, icon_size) if stem else None
        icon_x = x0 + pad
        if icon is not None:
            icon_y = content_mid_y - icon_size // 2
            _paste_icon(img, icon, (icon_x, icon_y))
            text_left = icon_x + icon_size + round(10 * s)
        else:
            text_left = x0 + pad

        # value left of center-right, pct on far right
        val_s = format_compact(val)
        pct_s = f"{pct}%"
        pct_w = draw.textlength(pct_s, font=f_pct)
        draw.text(
            (x1 - pad, content_mid_y),
            pct_s,
            fill=BLACK,
            font=f_pct,
            anchor="rm",
        )
        # value between icon and pct
        draw.text(
            (text_left, content_mid_y),
            val_s,
            fill=BLACK,
            font=f_val,
            anchor="lm",
        )

        # progress bar full width of card inner
        bar_x0 = x0 + pad
        bar_x1 = x1 - pad
        bar_w = bar_x1 - bar_x0
        _round_rect(
            draw,
            [bar_x0, bar_y, bar_x1, bar_y + bar_h],
            max(2, bar_h // 2),
            outline=BLACK,
            width=max(1, border - 1),
        )
        fill_w = int(bar_w * min(100, pct) / 100)
        if fill_w > 2:
            inset = 1
            # filled portion (red), rounded-ish left
            draw.rectangle(
                [
                    bar_x0 + inset,
                    bar_y + inset,
                    bar_x0 + max(inset + 1, fill_w - inset),
                    bar_y + bar_h - inset,
                ],
                fill=RED,
            )

    return img
