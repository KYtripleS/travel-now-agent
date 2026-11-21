"""Data cards for X posts (2026-11-21): 1200x675 PNGs in the brand colours, rendered with rsvg-convert.

The queue had 99 posts and no images. A post that carries its own numbers as a picture is read, saved and
shared without leaving X, which X's ranking rewards far more than a link click. Every figure on a card
comes from the facts ledger (data/facts/*.json); the fact ids are listed with each card. Recheck them
before reusing a card after its "checked" month.

Writes site/images/x/<name>.png and docs/images/x/<name>.png.
usage: .venv/bin/python ops/x_cards.py
"""
from __future__ import annotations

import shutil
import subprocess
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAVY, GOLD, CREAM, INK = "#172033", "#C9A84C", "#F8F4E9", "#5b6478"
SERIF = "Newsreader, Georgia, 'Times New Roman', serif"
SANS = "'Libre Franklin', Helvetica, Arial, sans-serif"
W, H = 1200, 675


def frame(kicker: str, title: str, body: str, foot: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="{CREAM}"/>
<rect x="0" y="0" width="{W}" height="14" fill="{NAVY}"/>
<text x="64" y="84" font-family="{SANS}" font-size="22" letter-spacing="3" fill="{GOLD}" font-weight="700">{escape(kicker.upper())}</text>
<text x="64" y="148" font-family="{SERIF}" font-size="50" font-weight="600" fill="{NAVY}">{escape(title)}</text>
<line x1="64" y1="178" x2="{W-64}" y2="178" stroke="{NAVY}" stroke-opacity=".18" stroke-width="2"/>
{body}
<line x1="64" y1="{H-74}" x2="{W-64}" y2="{H-74}" stroke="{NAVY}" stroke-opacity=".18" stroke-width="2"/>
<text x="64" y="{H-36}" font-family="{SANS}" font-size="20" fill="{INK}">{escape(foot)}</text>
<text x="{W-64}" y="{H-36}" text-anchor="end" font-family="{SERIF}" font-size="26" font-weight="600" fill="{NAVY}">Gently Yonder</text>
</svg>"""


def bars(rows: list[tuple[str, float, str]], top: int = 216, step: int = 60) -> str:
    mx = max(v for _, v, _ in rows) or 1
    out = []
    for i, (label, v, shown) in enumerate(rows):
        y = top + i * step
        w = 0 if v == 0 else max(6, int(560 * v / mx))
        out.append(f'<text x="64" y="{y+30}" font-family="{SANS}" font-size="27" fill="{NAVY}">{escape(label)}</text>')
        out.append(f'<rect x="330" y="{y+6}" width="{w}" height="34" fill="{GOLD if v else NAVY}" fill-opacity="{1 if v else .15}"/>')
        out.append(f'<text x="{330+w+16}" y="{y+32}" font-family="{SERIF}" font-size="30" font-weight="600" fill="{NAVY}">{escape(shown)}</text>')
    return "\n".join(out)


def lines(rows: list[tuple[str, str]], top: int = 236, step: int = 92) -> str:
    out = []
    for i, (big, small) in enumerate(rows):
        y = top + i * step
        out.append(f'<text x="64" y="{y}" font-family="{SERIF}" font-size="40" font-weight="600" fill="{NAVY}">{escape(big)}</text>')
        out.append(f'<text x="64" y="{y+36}" font-family="{SANS}" font-size="24" fill="{INK}">{escape(small)}</text>')
    return "\n".join(out)


CARDS = {
    # tourist-taxes-around-the-world-2026-data (key findings, ledger via data/tourist_taxes_2026.json)
    "tourist-tax-3-nights": frame(
        "Tourist tax, one standard stay", "What the tax adds to 3 nights",
        bars([("Chicago", 104, "about US$104"), ("Washington, DC", 96, "about US$96"),
              ("Amsterdam", 75, "US$75"), ("Paris", 57, "about US$57"),
              ("London", 0, "none"), ("Copenhagen", 0, "none")]),
        "2 adults, one US$200 room, 3 nights. Each city's official rule; check dates in our report."),
    # jp.tokyo.accommodation-tax-2027, at.vienna.ortstaxe-2026
    "hotel-tax-2027": frame(
        "Already announced", "Hotel taxes that rise in 2027",
        lines([("Tokyo, from 1 April 2027", "3% of the room rate per person per night, from ¥13,000; cheaper stays exempt"),
               ("Vienna, from 1 July 2027", "8% of the stay price, before VAT and breakfast (5% until then)")]),
        "Sources: Tokyo Metropolitan Government; City of Vienna. Checked October 2026."),
    # fi.rovaniemi.aurora.* (read 21 Nov 2026 for 12 Dec 2026)
    "aurora-tour-terms": frame(
        "Rovaniemi, 12 December", "Three aurora tours, three refund rules",
        lines([("€79", "Barbecue aurora tour: non-refundable, cannot be moved"),
               ("€85.44", "Small group of 2 to 8: free cancellation up to 2 days ahead"),
               ("€199", "Max 8, overalls included: full refund if no aurora shows on camera")]),
        "Partner listings read 21 Nov 2026. No tour can guarantee the aurora."),
    # jp.kyoto.new-year.chion-in-2025-terms, jp.tokyo.new-year.tmg-countdown, uk.london.wbstudio.snow-season
    "december-deadlines": frame(
        "Dates to put in your calendar", "December booking windows",
        lines([("1 Dec, 2pm JST", "Kyoto: Chion-in's New Year's Eve bell-viewing tickets go on sale online"),
               ("10 Dec, 11:59pm JST", "Tokyo: last day to enter the free Odaiba countdown lottery"),
               ("To 17 Jan 2027", "London: the studio tour's winter season; no tickets sold at the door")]),
        "From each organiser's own page, checked 20-21 Nov 2026."),
}


def main() -> None:
    out = REPO / "site" / "images" / "x"
    out.mkdir(parents=True, exist_ok=True)
    (REPO / "docs" / "images" / "x").mkdir(parents=True, exist_ok=True)
    for name, svg in CARDS.items():
        src = out / f"{name}.svg"
        src.write_text(svg, encoding="utf-8")
        png = out / f"{name}.png"
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), str(src), "-o", str(png)], check=True)
        shutil.copy(png, REPO / "docs" / "images" / "x" / png.name)
        src.unlink()
        print("card:", png.relative_to(REPO))


if __name__ == "__main__":
    main()
