"""
400×300 BWR e-ink AI Token panel.

Layout:
  - Top card: 30D TOTAL | TODAY + 30-day bar chart
  - Bottom: Codex | Grok cards (icon + 30d tokens + % + red bar)
"""

from __future__ import annotations

from functools import lru_cache
from math import floor, log10
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# Spec colors only
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (0xD7, 0x19, 0x20)  # #D71920

ICON_STEM = {"codex": "openai", "grok": "grok"}


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
            im = im.resize((size, size), Image.Resampling.NEAREST)
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
                px[x, y] = (0, 0, 0, 255)
            else:
                px[x, y] = (0, 0, 0, 0)
    return im


def _font(size: int, kind: str = "num") -> ImageFont.ImageFont:
    """
    kind: label | num | unit
    Prefer condensed / tabular-friendly fonts; fall back gracefully.
    """
    windir = Path(r"C:\Windows\Fonts")
    if kind == "num":
        names = [
            "RobotoCondensed-Bold.ttf",
            "ROBOTOCONDENSED-BOLD.TTF",
            "arialbd.ttf",
            "ARIALN.TTF",  # Arial Narrow
            "ARIALNB.TTF",
            "msyhbd.ttc",
            "msyh.ttc",
            "arial.ttf",
            "simhei.ttf",
        ]
    elif kind == "label":
        names = [
            "RobotoCondensed-Bold.ttf",
            "arialbd.ttf",
            "ARIALN.TTF",
            "msyhbd.ttc",
            "msyh.ttc",
            "arial.ttf",
        ]
    else:  # unit / small
        names = [
            "msyhbd.ttc",
            "msyh.ttc",
            "arialbd.ttf",
            "arial.ttf",
            "simhei.ttf",
        ]

    candidates: list[Path] = []
    if windir.is_dir():
        for n in names:
            candidates.append(windir / n)
    candidates += [
        Path("/usr/share/fonts/truetype/roboto/hinted/RobotoCondensed-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _sig_str(v: float, sig: int = 4) -> str:
    if v == 0:
        return "0"
    if v < 0:
        v = abs(v)
    order = floor(log10(v)) if v > 0 else 0
    decimals = max(0, sig - order - 1)
    rounded = round(v, decimals)
    if rounded >= 1000:
        return f"{rounded:.0f}"
    if decimals == 0:
        return str(int(rounded))
    s = f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")
    return s


def format_value_parts(n: float) -> tuple[str, str]:
    """
    Returns (number_str, unit) with max 4 significant digits.
    Units: '' | K | M | B | T. Auto-upgrade if rounds to 1000.
    """
    n = abs(float(n))
    if n < 1000:
        return str(int(round(n))), ""

    chain = [
        ("K", 1e3),
        ("M", 1e6),
        ("B", 1e9),
        ("T", 1e12),
    ]
    # pick largest unit where n >= div
    idx = 0
    for i, (unit, div) in enumerate(chain):
        if n >= div:
            idx = i
    unit, div = chain[idx]
    s = _sig_str(n / div, 4)
    try:
        fv = float(s)
    except ValueError:
        fv = n / div
    # upgrade if >= 1000
    while fv >= 1000 - 1e-9 and idx + 1 < len(chain):
        idx += 1
        unit, div = chain[idx]
        s = _sig_str(n / div, 4)
        try:
            fv = float(s)
        except ValueError:
            break
    return s, unit


def _draw_value(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    n: float,
    *,
    num_size: int,
    color: tuple[int, int, int],
    anchor: str = "lt",
    max_width: int | None = None,
) -> tuple[int, int]:
    """
    Draw number + unit (unit ~55-60% height, baseline-aligned).
    Returns (width, height) of drawn block.
    """
    num_s, unit = format_value_parts(n)
    size = num_size
    f_num = _font(size, "num")
    f_unit = _font(max(10, int(size * 0.58)), "unit")

    def measure(fn, fu):
        nb = draw.textbbox((0, 0), num_s, font=fn)
        nw = nb[2] - nb[0]
        nh = nb[3] - nb[1]
        if unit:
            ub = draw.textbbox((0, 0), unit, font=fu)
            uw = ub[2] - ub[0]
            uh = ub[3] - ub[1]
        else:
            uw = uh = 0
        gap = max(2, size // 12) if unit else 0
        return nw + gap + uw, max(nh, uh), nw, gap

    w, h, nw, gap = measure(f_num, f_unit)
    while max_width is not None and w > max_width and size > 14:
        size -= 1
        f_num = _font(size, "num")
        f_unit = _font(max(9, int(size * 0.58)), "unit")
        w, h, nw, gap = measure(f_num, f_unit)

    ax, ay = xy
    if anchor == "mm":
        x, y = ax - w // 2, ay - h // 2
    elif anchor == "lm":
        x, y = ax, ay - h // 2
    elif anchor == "rm":
        x, y = ax - w, ay - h // 2
    else:  # lt
        x, y = ax, ay

    num_bb = draw.textbbox((0, 0), num_s, font=f_num)
    num_h = num_bb[3] - num_bb[1]
    draw.text((x, y), num_s, font=f_num, fill=color)
    if unit:
        unit_bb = draw.textbbox((0, 0), unit, font=f_unit)
        unit_h = unit_bb[3] - unit_bb[1]
        ux = x + nw + gap
        uy = y + num_h - unit_h
        draw.text((ux, uy), unit, font=f_unit, fill=color)
    return w, h


def _round_rect(draw: ImageDraw.ImageDraw, box, radius: int, **kwargs) -> None:
    try:
        draw.rounded_rectangle(box, radius=radius, **kwargs)
    except Exception:
        draw.rectangle(box, **kwargs)


def quantize_exact_bwr(img: Image.Image) -> Image.Image:
    """Force pure #FFFFFF / #000000 / #D71920 only."""
    img = img.convert("RGB")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # red if R dominant
            if r > 140 and r > g * 1.25 and r > b * 1.25:
                px[x, y] = RED
            elif 0.299 * r + 0.587 * g + 0.114 * b < 140:
                px[x, y] = BLACK
            else:
                px[x, y] = WHITE
    return img


def render_token(width: int, height: int, data: dict[str, Any]) -> Image.Image:
    """
    data keys from fetch_dashboard_usage:
      total_30d, today_total, codex_30d, grok_30d,
      codex_pct, grok_pct, daily[30], start_label, end_label
    """
    assert width == 400 and height == 300, "canvas must be 400×300"
    img = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(img)

    margin = 4
    gap = 5
    border = 2
    card_r = 7
    bar_r = 3

    total_30d = float(data.get("total_30d") or data.get("total") or 0)
    today_total = float(data.get("today_total") or 0)
    codex_30d = float(data.get("codex_30d") or data.get("codex") or 0)
    grok_30d = float(data.get("grok_30d") or data.get("grok") or 0)
    codex_pct = int(data.get("codex_pct") or 0)
    grok_pct = int(data.get("grok_pct") or 0)
    if codex_30d + grok_30d > 0 and (codex_pct + grok_pct != 100):
        codex_pct = round(codex_30d / (codex_30d + grok_30d) * 100)
        grok_pct = 100 - codex_pct

    daily = list(data.get("daily") or [0] * 30)
    if len(daily) < 30:
        daily = [0] * (30 - len(daily)) + daily
    daily = daily[-30:]
    start_label = str(data.get("start_label") or "")
    end_label = str(data.get("end_label") or "")

    # —— Top card 392×200 @ (4,4) ——
    top_x, top_y = margin, margin
    top_w, top_h = width - margin * 2, 200
    _round_rect(
        draw,
        [top_x, top_y, top_x + top_w, top_y + top_h],
        card_r,
        outline=BLACK,
        width=border,
    )

    # metrics row height ~78
    metrics_h = 78
    split_x = top_x + int(top_w * 0.56)
    # vertical divider
    div_top = top_y + 14
    div_bot = top_y + metrics_h - 8
    draw.line([(split_x, div_top), (split_x, div_bot)], fill=BLACK, width=2)

    f_lab = _font(13, "label")
    # LEFT: 30D TOTAL
    draw.text((top_x + 12, top_y + 10), "30D TOTAL", font=f_lab, fill=BLACK)
    _draw_value(
        draw,
        (top_x + 12, top_y + 32),
        total_30d,
        num_size=42,
        color=BLACK,
        anchor="lt",
        max_width=split_x - top_x - 24,
    )

    # RIGHT: TODAY (red)
    draw.text((split_x + 14, top_y + 10), "TODAY", font=f_lab, fill=BLACK)
    _draw_value(
        draw,
        (split_x + 14, top_y + 32),
        today_total,
        num_size=42,
        color=RED,
        anchor="lt",
        max_width=top_x + top_w - split_x - 26,
    )

    # —— Bar chart area ——
    chart_top = top_y + metrics_h
    chart_bot = top_y + top_h - 22
    chart_left = top_x + 14
    chart_right = top_x + top_w - 14
    chart_w = chart_right - chart_left
    chart_h = chart_bot - chart_top

    n_bars = 30
    gap_b = 2
    bar_w = max(2, (chart_w - gap_b * (n_bars - 1)) // n_bars)
    # recompute to fill width evenly
    total_bars_w = bar_w * n_bars + gap_b * (n_bars - 1)
    chart_left = top_x + 14 + (chart_w - total_bars_w) // 2

    max_v = max(daily) if daily else 1
    if max_v <= 0:
        max_v = 1

    for i, v in enumerate(daily):
        is_recent5 = i >= n_bars - 5
        is_today = i == n_bars - 1
        bw = bar_w + (1 if is_today else 0)
        x = chart_left + i * (bar_w + gap_b)
        if is_today:
            x = chart_left + i * (bar_w + gap_b) - 0  # keep grid
        h = max(2, int(chart_h * (v / max_v)))
        if is_today:
            h = min(chart_h, int(h * 1.08) + 2)  # slightly taller
        y1 = chart_bot
        y0 = y1 - h
        color = RED if is_recent5 else BLACK
        draw.rectangle([x, y0, x + bw - 1, y1 - 1], fill=color)

    # date labels under chart
    f_date = _font(11, "unit")
    draw.text((top_x + 12, top_y + top_h - 16), start_label, font=f_date, fill=BLACK)
    eb = draw.textbbox((0, 0), end_label, font=f_date)
    ew = eb[2] - eb[0]
    draw.text(
        (top_x + top_w - 12 - ew, top_y + top_h - 16),
        end_label,
        font=f_date,
        fill=BLACK,
    )

    # —— Bottom vendor cards ——
    bottom_y = top_y + top_h + gap
    bottom_h = height - margin - bottom_y  # ~88
    card_w = (width - margin * 2 - gap) // 2

    _draw_vendor_card(
        img,
        draw,
        margin,
        bottom_y,
        card_w,
        bottom_h,
        stem="openai",
        tokens=codex_30d,
        pct=codex_pct,
        border=border,
        card_r=card_r,
        bar_r=bar_r,
    )
    _draw_vendor_card(
        img,
        draw,
        margin + card_w + gap,
        bottom_y,
        card_w,
        bottom_h,
        stem="grok",
        tokens=grok_30d,
        pct=grok_pct,
        border=border,
        card_r=card_r,
        bar_r=bar_r,
    )

    return quantize_exact_bwr(img)


def _draw_vendor_card(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    stem: str,
    tokens: float,
    pct: int,
    border: int,
    card_r: int,
    bar_r: int,
) -> None:
    """
    Row layout (single horizontal center line above progress bar):
      [ icon 38px ] --10px-- [ number + unit ] ........ [ pct% ]
    Icon and token number share the same vertical midpoint.
    """
    _round_rect(draw, [x, y, x + w, y + h], card_r, outline=BLACK, width=border)

    pad = 10
    icon_size = 38
    icon_gap = 10  # icon → number
    bar_h = 10
    bar_y = y + h - pad - bar_h
    # content band above bar
    content_top = y + pad
    content_bot = bar_y - 4
    mid_y = (content_top + content_bot) // 2

    # —— icon (vertically centered on mid_y) ——
    icon = load_icon(stem, icon_size)
    text_left = x + pad
    if icon is not None:
        iy = mid_y - icon_size // 2
        img.paste(icon, (x + pad, iy), icon)
        text_left = x + pad + icon_size + icon_gap

    # —— percent: fixed right, same mid_y ——
    pct_gutter = 44
    f_pct = _font(15, "unit")
    pct_s = f"{int(pct)}%"
    try:
        draw.text(
            (x + w - pad, mid_y),
            pct_s,
            font=f_pct,
            fill=BLACK,
            anchor="rm",
        )
    except TypeError:
        pb = draw.textbbox((0, 0), pct_s, font=f_pct)
        pw, ph = pb[2] - pb[0], pb[3] - pb[1]
        draw.text((x + w - pad - pw, mid_y - ph // 2), pct_s, font=f_pct, fill=BLACK)

    # —— token number + unit, left-middle on mid_y (same horizontal line as icon) ——
    max_w = max(24, x + w - pad - pct_gutter - text_left)
    num_s, unit = format_value_parts(tokens)
    size = 28
    f_num = _font(size, "num")
    f_unit = _font(max(12, int(size * 0.58)), "unit")

    def _w(fn, fu):
        nb = draw.textbbox((0, 0), num_s, font=fn)
        nw = nb[2] - nb[0]
        if unit:
            ub = draw.textbbox((0, 0), unit, font=fu)
            return nw + max(2, size // 12) + (ub[2] - ub[0])
        return nw

    while _w(f_num, f_unit) > max_w and size > 14:
        size -= 1
        f_num = _font(size, "num")
        f_unit = _font(max(10, int(size * 0.58)), "unit")

    gap_u = max(2, size // 12) if unit else 0
    try:
        # Pillow anchor: left-middle — same center line as icon
        draw.text((text_left, mid_y), num_s, font=f_num, fill=BLACK, anchor="lm")
        if unit:
            nw = draw.textbbox((0, 0), num_s, font=f_num)[2] - draw.textbbox((0, 0), num_s, font=f_num)[0]
            # unit: left-middle, slightly lower optical baseline with smaller font still centered
            draw.text(
                (text_left + nw + gap_u, mid_y),
                unit,
                font=f_unit,
                fill=BLACK,
                anchor="lm",
            )
    except TypeError:
        # fallback without anchor
        nb = draw.textbbox((0, 0), num_s, font=f_num)
        nh = nb[3] - nb[1]
        ty = mid_y - nh // 2 - nb[1]
        draw.text((text_left, ty), num_s, font=f_num, fill=BLACK)
        if unit:
            nw = nb[2] - nb[0]
            ub = draw.textbbox((0, 0), unit, font=f_unit)
            uh = ub[3] - ub[1]
            draw.text(
                (text_left + nw + gap_u, mid_y - uh // 2 - ub[1]),
                unit,
                font=f_unit,
                fill=BLACK,
            )

    # progress bar
    bar_x0 = x + pad
    bar_x1 = x + w - pad
    bar_w = bar_x1 - bar_x0
    _round_rect(
        draw,
        [bar_x0, bar_y, bar_x1, bar_y + bar_h],
        bar_r,
        outline=BLACK,
        width=1,
    )
    fill_w = int(bar_w * min(100, max(0, pct)) / 100)
    if fill_w > 2:
        draw.rectangle(
            [bar_x0 + 1, bar_y + 1, bar_x0 + fill_w - 1, bar_y + bar_h - 1],
            fill=RED,
        )
