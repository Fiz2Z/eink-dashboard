"""One-shot: SVG icons -> black PNG for Pillow."""
from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = ROOT / "assets" / "icons"
NAMES = ["openai", "anthropic", "grok", "deepseek"]


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        svg_path = ICON_DIR / f"{name}.svg"
        text = svg_path.read_text(encoding="utf-8")
        if "fill=" not in text[:300]:
            text = text.replace("<svg", '<svg fill="#000000"', 1)
        doc = fitz.open(stream=text.encode("utf-8"), filetype="svg")
        page = doc[0]
        mat = fitz.Matrix(10, 10)
        pix = page.get_pixmap(matrix=mat, alpha=True)
        png_path = ICON_DIR / f"{name}.png"
        pix.save(str(png_path))
        im = Image.open(png_path).convert("RGBA")
        # ensure black marks on transparent
        px = im.load()
        w, h = im.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a < 10:
                    continue
                # any visible pixel -> pure black
                if r + g + b < 700:
                    px[x, y] = (0, 0, 0, 255)
        im.save(png_path)
        print(name, im.size, png_path)


if __name__ == "__main__":
    main()
