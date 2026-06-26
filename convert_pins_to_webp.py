#!/usr/bin/env python3
"""
convert_pins_to_webp.py

Generates a .webp copy alongside each Pinterest pin PNG in
site/images/pinterest/ and docs/images/pinterest/. The PNG stays in
place (it is what Pinterest itself prefers when you upload). The WebP
is what the homepage carousel actually serves via <picture><source>,
which cuts page weight by ~90% on every visit.

Run after generating a new wave of pins (generate_pin_wave.py 2 or 3,
or generate_pin.py one-off).

Idempotent — skips files that already have a WebP twin.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow not installed (pip install Pillow)")

REPO = Path(__file__).resolve().parent
WEBP_QUALITY = 82
WEBP_METHOD = 6  # 0=fastest, 6=best compression (slower)


def convert_all() -> None:
    new = skipped = 0
    total_png = total_webp = 0
    for base in ("site", "docs"):
        pin_dir = REPO / base / "images" / "pinterest"
        if not pin_dir.exists():
            continue
        for png_path in sorted(pin_dir.glob("*.png")):
            webp_path = png_path.with_suffix(".webp")
            png_size = png_path.stat().st_size
            total_png += png_size
            if webp_path.exists() and webp_path.stat().st_size > 0:
                total_webp += webp_path.stat().st_size
                skipped += 1
                continue
            img = Image.open(png_path)
            img.save(webp_path, "WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)
            total_webp += webp_path.stat().st_size
            new += 1
            print(f"  {base}/{png_path.name}: {png_size/1024:.0f} KB → {webp_path.stat().st_size/1024:.0f} KB")

    print()
    print(f"  new conversions : {new}")
    print(f"  already present : {skipped}")
    print(f"  total PNG size  : {total_png/1024/1024:.2f} MB")
    print(f"  total WebP size : {total_webp/1024/1024:.2f} MB")
    if total_png:
        print(f"  reduction       : {(1 - total_webp/total_png)*100:.1f}%")


if __name__ == "__main__":
    convert_all()
