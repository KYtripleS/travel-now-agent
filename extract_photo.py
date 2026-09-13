#!/usr/bin/env python3
"""Pull the real photograph out of a Pinterest pin SVG.

Every image under site/images/pinterest/ is a 1000x1500 *pin*: a photo with a
navy overlay, a title and a "Read the guide" CTA burned into it. Reusing one as
an article figure puts an advert for a different article in the middle of the
page — which is exactly how "Sydney: A first-timer's guide" ended up inside a
booking-platform comparison.

The photograph itself is embedded in the pin's SVG as base64. This lifts it out
and writes a clean landscape crop with no text on it, into site/images/photos/.
"""
from __future__ import annotations

import argparse
import base64
import io
import re
import shutil
from pathlib import Path

from PIL import Image

SRC_DIR = Path("site/images/pinterest")
OUT_DIR = Path("site/images/photos")
DOCS_DIR = Path("docs/images/photos")
RATIO = 3 / 2          # landscape crop; 16:9 gets too letterboxed at this height
QUALITY = 82
VERTICAL_BIAS = 0.42   # crop slightly above centre — skylines sit high in these


def extract(name: str) -> Path | None:
    svg = SRC_DIR / f"{name}.svg"
    if not svg.exists():
        print(f"  {name:28} no SVG — skipped")
        return None
    m = re.search(r'xlink:href="data:image/(\w+);base64,([^"]+)"', svg.read_text(encoding="utf-8"))
    if not m:
        print(f"  {name:28} no embedded photo — skipped")
        return None

    im = Image.open(io.BytesIO(base64.b64decode(m.group(2)))).convert("RGB")
    w, h = im.size
    crop_h = min(h, int(w / RATIO))
    top = max(0, min(h - crop_h, int((h - crop_h) * VERTICAL_BIAS)))
    im = im.crop((0, top, w, top + crop_h))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{name}.webp"
    im.save(out, "WEBP", quality=QUALITY, method=6)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, DOCS_DIR / out.name)
    print(f"  {name:28} {w}x{h} -> {im.size[0]}x{im.size[1]}  {out.stat().st_size // 1024}KB")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("names", nargs="+", help="pin basenames, without extension")
    args = ap.parse_args()
    for n in args.names:
        extract(n)


if __name__ == "__main__":
    main()
