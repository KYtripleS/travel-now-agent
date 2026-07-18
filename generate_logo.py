#!/usr/bin/env python3
"""
generate_logo.py — the GY brand mark, reproducibly.

Blue squircle, white geometric G, green Y. All letterforms are hand-drawn
paths (no font dependency), round caps to echo the "gently" voice. The G
follows true geometric-G anatomy: the stroke runs from the upper-right
terminal the long way around (top, left, bottom), climbs the right side to
just under mid-height, then turns inward as the horizontal bar.

Outputs (site/ + docs/): favicon.svg, favicon-{48,96,192,512}.png,
apple-touch-icon.png (solid background), images/brand/gy-logo.svg.
Requires rsvg-convert (librsvg).  Usage: python3 generate_logo.py
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent
BLUE, GREEN, WHITE = "#2456A6", "#3BB273", "#FFFFFF"
S = 512
CX = CY = S / 2
LR, LW = 92, 46            # letter radius, stroke width
GX, YX = CX - 104, CX + 108


def pt(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return (cx + r * math.cos(rad), cy + r * math.sin(rad))


def g_path(cx: float, cy: float, r: float) -> str:
    x1, y1 = pt(cx, cy, r, -55)   # upper lip of the mouth
    x2, y2 = pt(cx, cy, r, 5)     # right side, just under mid-height
    return (f"M {x1:.1f} {y1:.1f} A {r} {r} 0 1 0 {x2:.1f} {y2:.1f} "
            f"L {cx + 6:.1f} {y2:.1f}")


def y_paths(cx: float, cy: float, r: float) -> list[str]:
    top, join, bottom, spread = cy - r, cy - r * 0.08, cy + r, r * 0.82
    return [f"M {cx - spread:.1f} {top:.1f} L {cx:.1f} {join:.1f}",
            f"M {cx + spread:.1f} {top:.1f} L {cx:.1f} {join:.1f}",
            f"M {cx:.1f} {join:.1f} L {cx:.1f} {bottom:.1f}"]


def stroke(d: str, color: str, w: int) -> str:
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def letters() -> str:
    parts = [stroke(g_path(GX, CY, LR), WHITE, LW)]
    parts += [stroke(d, GREEN, LW) for d in y_paths(YX, CY, LR)]
    return "\n".join(parts)


def svg(background: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">\n'
            f"{background}\n{letters()}\n</svg>")


def main() -> None:
    squircle = f'<rect x="16" y="16" width="{S-32}" height="{S-32}" rx="120" fill="{BLUE}"/>'
    square = f'<rect width="{S}" height="{S}" fill="{BLUE}"/>'
    final, apple = svg(squircle), svg(square)

    tmp = REPO / "images_tmp_logo.svg"
    tmp.write_text(final)
    tmp_apple = REPO / "images_tmp_apple.svg"
    tmp_apple.write_text(apple)
    try:
        for base in ("site", "docs"):
            b = REPO / base
            (b / "favicon.svg").write_text(final)
            (b / "images" / "brand").mkdir(parents=True, exist_ok=True)
            (b / "images" / "brand" / "gy-logo.svg").write_text(final)
            for w in (48, 96, 192, 512):
                subprocess.run(["rsvg-convert", "-w", str(w), "-h", str(w),
                                str(tmp), "-o", str(b / f"favicon-{w}.png")],
                               check=True)
            subprocess.run(["rsvg-convert", "-w", "180", "-h", "180",
                            str(tmp_apple), "-o", str(b / "apple-touch-icon.png")],
                           check=True)
    finally:
        tmp.unlink(missing_ok=True)
        tmp_apple.unlink(missing_ok=True)
    print("GY mark regenerated into site/ and docs/ (svg + 48/96/192/512 + apple 180)")


if __name__ == "__main__":
    main()
