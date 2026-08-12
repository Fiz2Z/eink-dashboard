"""Pack Pillow images into EPD-nRF5 black/red bitplanes."""

from __future__ import annotations

from PIL import Image

# 1 = white/off pigment, 0 = pigment on (matches web host)


RED = (0xD7, 0x19, 0x20)  # #D71920


def _is_red(r: int, g: int, b: int, red_ratio: float = 1.25) -> bool:
    return r > 140 and r > g * red_ratio and r > b * red_ratio


def _is_black(r: int, g: int, b: int, dark: int = 140) -> bool:
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return lum < dark


def quantize_bw_red(img: Image.Image) -> Image.Image:
    """Snap to pure #FFFFFF / #000000 / #D71920 for BWR panels."""
    img = img.convert("RGB")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if _is_red(r, g, b):
                px[x, y] = RED
            elif _is_black(r, g, b):
                px[x, y] = (0, 0, 0)
            else:
                px[x, y] = (255, 255, 255)
    return img


def pack_planes(img: Image.Image) -> tuple[bytes, bytes]:
    """
    Returns (bw_plane, red_plane), each row-major, ceil(w/8)*h bytes.
    Black plane: black→0, white&red→1
    Red plane: red→0, white&black→1
    """
    img = img.convert("RGB")
    w, h = img.size
    row_bytes = (w + 7) // 8
    bw = bytearray(row_bytes * h)
    red = bytearray(row_bytes * h)
    px = img.load()
    oi = 0
    for y in range(h):
        for xb in range(row_bytes):
            bw_byte = 0
            red_byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                is_black = False
                is_red = False
                if x < w:
                    r, g, b = px[x, y]
                    is_red = _is_red(r, g, b)
                    is_black = (not is_red) and _is_black(r, g, b)
                bw_byte = (bw_byte << 1) | (0 if is_black else 1)
                red_byte = (red_byte << 1) | (0 if is_red else 1)
            bw[oi] = bw_byte
            red[oi] = red_byte
            oi += 1
    return bytes(bw), bytes(red)


def load_and_fit(path: str, width: int, height: int) -> Image.Image:
    img = Image.open(path).convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    return quantize_bw_red(img)
