#!/usr/bin/env python3
"""
build_lead_magnet.py

Render the Travel Now "Pre-Flight Checklist" lead magnet as a branded
2-page A4 PDF. This is the incentive that turns a newsletter CTA into a
signup: "Get the free printable checklist."

Pipeline (uses only tooling already on the machine):
  SVG page  --rsvg-convert-->  PNG  --Pillow-->  combined multi-page PDF

Output:
  site/downloads/travel-now-preflight-checklist.pdf
  docs/downloads/travel-now-preflight-checklist.pdf   (mirror)

The content is sourced from our own published guides (liquids rule,
battery rule, eSIM prep, passport validity) so it stays consistent with
the site and the editorial standards.

Usage:
  python build_lead_magnet.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent
SITE_OUT = REPO / "site" / "downloads" / "travel-now-preflight-checklist.pdf"
DOCS_OUT = REPO / "docs" / "downloads" / "travel-now-preflight-checklist.pdf"

# A4 at 150 dpi
W, H = 1240, 1754
NAVY = "#172033"
NAVY_2 = "#1f2b45"
GOLD = "#C9A84C"
CREAM = "#F8F4E9"
MUTED = "#9aa6bd"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def checkbox(x: int, y: int) -> str:
    return (f'<rect x="{x}" y="{y}" width="30" height="30" rx="5" '
            f'fill="none" stroke="{GOLD}" stroke-width="2.5"/>')


def checklist_block(x: int, y: int, heading: str, items: list[str], line_h: int = 64) -> str:
    parts = [
        f'<text x="{x}" y="{y}" font-family="Georgia, serif" font-size="34" '
        f'font-weight="700" fill="{GOLD}" letter-spacing="1">{esc(heading)}</text>'
    ]
    cy = y + 48
    for item in items:
        parts.append(checkbox(x, cy - 24))
        parts.append(
            f'<text x="{x + 48}" y="{cy}" font-family="Georgia, serif" '
            f'font-size="27" fill="{CREAM}">{esc(item)}</text>'
        )
        cy += line_h
    return "\n".join(parts), cy


def page1_svg() -> str:
    body = []
    # background
    body.append(f'<rect width="{W}" height="{H}" fill="{NAVY}"/>')
    body.append(f'<rect x="0" y="0" width="{W}" height="14" fill="{GOLD}"/>')
    # header
    body.append(f'<text x="{W/2}" y="120" font-family="Georgia, serif" font-size="30" '
                f'fill="{GOLD}" text-anchor="middle" letter-spacing="10">TRAVEL NOW</text>')
    body.append(f'<line x1="{W/2-90}" y1="148" x2="{W/2+90}" y2="148" stroke="{GOLD}" stroke-width="2"/>')
    body.append(f'<text x="{W/2}" y="245" font-family="Georgia, serif" font-size="78" '
                f'font-weight="700" fill="{CREAM}" text-anchor="middle" letter-spacing="-1">Pre-Flight Checklist</text>')
    body.append(f'<text x="{W/2}" y="300" font-family="Georgia, serif" font-size="30" '
                f'font-style="italic" fill="{MUTED}" text-anchor="middle">The 10-minute run-through to do the night before you fly</text>')

    # two columns of checklists
    left_x, right_x = 110, 660
    y0 = 400

    block, _ = checklist_block(left_x, y0, "DOCUMENTS", [
        "Passport valid 6+ months past return",
        "Visa / eTA secured & printed",
        "Boarding pass saved offline",
        "Hotel address saved offline",
        "Copy of passport (photo + cloud)",
    ])
    body.append(block)

    block, _ = checklist_block(left_x, y0 + 380, "MONEY", [
        "Cards told you're travelling",
        "Some local cash for arrival",
        "Backup card stored separately",
        "Travel insurance purchased",
    ])
    body.append(block)

    block, _ = checklist_block(right_x, y0, "CONNECTIVITY", [
        "eSIM installed (left inactive)",
        "Maps downloaded offline",
        "Power bank charged (carry-on)",
        "Chargers + universal adapter",
        "Translation app downloaded",
    ])
    body.append(block)

    block, _ = checklist_block(right_x, y0 + 380, "CARRY-ON", [
        "Liquids in 100ml / 1-quart bag",
        "Laptop & tablet easy to reach",
        "Medication in original packaging",
        "Lithium batteries in carry-on only",
    ])
    body.append(block)

    # footer tip strip
    body.append(f'<rect x="80" y="1480" width="{W-160}" height="150" rx="16" fill="{NAVY_2}"/>')
    body.append(f'<rect x="80" y="1480" width="8" height="150" fill="{GOLD}"/>')
    body.append(f'<text x="120" y="1540" font-family="Georgia, serif" font-size="26" '
                f'font-weight="700" fill="{GOLD}">Do this the night before — not the morning of.</text>')
    body.append(f'<text x="120" y="1582" font-family="Georgia, serif" font-size="23" '
                f'fill="{CREAM}">A calm setup at home beats a panicked repack at the security line.</text>')
    body.append(f'<text x="120" y="1614" font-family="Georgia, serif" font-size="23" '
                f'fill="{CREAM}">Page 1 of 2 — the rules cheat-sheet is on the next page.</text>')

    body.append(f'<text x="{W/2}" y="1710" font-family="Georgia, serif" font-size="22" '
                f'fill="{MUTED}" text-anchor="middle">travelnow • kytriples.github.io/travel-now-agent</text>')

    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n' + "\n".join(body) + "\n</svg>"


def rule_card(x: int, y: int, w: int, title: str, lines: list[str]) -> str:
    h = 60 + len(lines) * 40
    parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{NAVY_2}"/>',
             f'<rect x="{x}" y="{y}" width="8" height="{h}" fill="{GOLD}"/>',
             f'<text x="{x+34}" y="{y+48}" font-family="Georgia, serif" font-size="29" '
             f'font-weight="700" fill="{GOLD}">{esc(title)}</text>']
    ly = y + 90
    for ln in lines:
        parts.append(f'<text x="{x+34}" y="{ly}" font-family="Georgia, serif" font-size="24" '
                     f'fill="{CREAM}">{esc(ln)}</text>')
        ly += 40
    return "\n".join(parts)


def page2_svg() -> str:
    body = [f'<rect width="{W}" height="{H}" fill="{NAVY}"/>',
            f'<rect x="0" y="0" width="{W}" height="14" fill="{GOLD}"/>']
    body.append(f'<text x="{W/2}" y="120" font-family="Georgia, serif" font-size="30" '
                f'fill="{GOLD}" text-anchor="middle" letter-spacing="10">TRAVEL NOW</text>')
    body.append(f'<text x="{W/2}" y="220" font-family="Georgia, serif" font-size="64" '
                f'font-weight="700" fill="{CREAM}" text-anchor="middle">Security Rules Cheat-Sheet</text>')
    body.append(f'<text x="{W/2}" y="270" font-family="Georgia, serif" font-size="27" '
                f'font-style="italic" fill="{MUTED}" text-anchor="middle">The rules travelers trip over most — verify the live version before you fly</text>')

    body.append(rule_card(110, 330, 1020, "Liquids — the 100ml rule", [
        "Containers max 100ml (3.4oz) each, in one clear ~1-litre bag.",
        "Bag comes out of the carry-on for separate screening.",
        "Medication, baby formula & breast milk are exempt — declare them.",
    ]))
    body.append(rule_card(110, 540, 1020, "Batteries & power banks", [
        "Power banks and spare lithium batteries: carry-on ONLY, never checked.",
        "Common limit 100Wh; 100-160Wh often needs airline approval.",
        "Keep them in your personal item, not the overhead bag if gate-checked.",
    ]))
    body.append(rule_card(110, 750, 1020, "Electronics", [
        "Laptops & large tablets usually come out into a separate tray.",
        "Newer CT scanners may waive this — follow the signs at your lane.",
    ]))
    body.append(rule_card(110, 910, 1020, "Documents", [
        "Many countries require 6+ months passport validity beyond return.",
        "A valid passport or visa does not guarantee entry — officers decide.",
        "Name on booking must match your ID exactly.",
    ]))
    body.append(rule_card(110, 1120, 1020, "At the checkpoint", [
        "Empty pockets fully before the body scanner — coins, phone, wallet.",
        "Remove coat/jacket and often belt; slip-on shoes save time.",
        "Pack the liquids bag and laptop where you can grab them fast.",
    ]))

    # CTA strip
    body.append(f'<rect x="110" y="1360" width="1020" height="190" rx="18" fill="{GOLD}"/>')
    body.append(f'<text x="{W/2}" y="1430" font-family="Georgia, serif" font-size="34" '
                f'font-weight="700" fill="{NAVY}" text-anchor="middle">Want the full guides behind this checklist?</text>')
    body.append(f'<text x="{W/2}" y="1480" font-family="Georgia, serif" font-size="26" '
                f'fill="{NAVY}" text-anchor="middle">Airport security, eSIM setup, insurance &amp; packing — all free at:</text>')
    body.append(f'<text x="{W/2}" y="1522" font-family="Georgia, serif" font-size="27" '
                f'font-weight="700" fill="{NAVY}" text-anchor="middle">kytriples.github.io/travel-now-agent</text>')

    body.append(f'<text x="{W/2}" y="1660" font-family="Georgia, serif" font-size="21" '
                f'fill="{MUTED}" text-anchor="middle" width="900">Rules change often and vary by airport. This sheet is preparation guidance, not a guarantee —</text>')
    body.append(f'<text x="{W/2}" y="1688" font-family="Georgia, serif" font-size="21" '
                f'fill="{MUTED}" text-anchor="middle">always confirm current rules with your airline and departure airport.</text>')
    body.append(f'<text x="{W/2}" y="1726" font-family="Georgia, serif" font-size="20" '
                f'fill="{MUTED}" text-anchor="middle">Page 2 of 2 • © Travel Now</text>')

    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n' + "\n".join(body) + "\n</svg>"


def render_png(svg: str, png_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg)
        svg_path = f.name
    subprocess.run(
        ["rsvg-convert", "-w", str(W), "-h", str(H), svg_path, "-o", str(png_path)],
        check=True,
    )
    Path(svg_path).unlink(missing_ok=True)


def main() -> None:
    SITE_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "p1.png"
        p2 = Path(td) / "p2.png"
        render_png(page1_svg(), p1)
        render_png(page2_svg(), p2)
        img1 = Image.open(p1).convert("RGB")
        img2 = Image.open(p2).convert("RGB")
        img1.save(SITE_OUT, "PDF", resolution=150.0, save_all=True, append_images=[img2])
    # mirror
    DOCS_OUT.write_bytes(SITE_OUT.read_bytes())
    kb = SITE_OUT.stat().st_size / 1024
    print(f"  wrote {SITE_OUT.relative_to(REPO)} ({kb:.0f} KB, 2 pages)")
    print(f"  mirrored to {DOCS_OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
