#!/usr/bin/env python3
"""
build_map.py — generate the Asia-Pacific destination map for the homepage.

Reads data/knowledge.json and renders an elegant, lightweight interactive SVG
into index.html between the BEGIN/END apac-map markers (same idempotent pattern
as build_carousel.py). Each covered country is a node sized by guide count;
hover/focus reveals its cities; click opens its hub (or its lead guide).

The map is navigation, not cartography — countries are placed at hand-set,
roughly-geographic coordinates on a soft dot-grid field. No mapping engine,
no heavy JS. Node data (cities, counts, links) comes from the knowledge graph.

Usage:  python build_map.py            # writes site/ + docs/ index.html
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"
MARK_BEGIN = "<!-- BEGIN apac-map (managed by build_map.py) -->"
MARK_END = "<!-- END apac-map -->"

# Hand-placed, roughly-geographic coordinates on a 0..960 x 0..620 field.
# Spread to fill the canvas (map is navigation, not cartography) and spaced so
# no node sits on a neighbour's label.
COORDS: dict[str, tuple[int, int]] = {
    "Thailand":    (150, 300),
    "Vietnam":     (300, 262),
    "Hong Kong":   (420, 300),
    "Malaysia":    (168, 432),
    "Singapore":   (250, 494),
    "Indonesia":   (398, 508),
    "Taiwan":      (556, 250),
    "Philippines": (602, 388),
    "South Korea": (668, 196),
    "Japan":       (812, 176),
    "Australia":   (836, 548),
}


# A subtle cartographic graticule (globe-style lat/long grid). Reads as a map
# surface — clean and premium — without pretending to hand-draw coastlines.
# Accurate country landmasses would need a real simplified SVG world-map asset.
GRID = """    <g class="apac-grid" aria-hidden="true">
      <path d="M40 132 Q480 106 920 132"/>
      <path d="M40 240 Q480 214 920 240"/>
      <path d="M40 348 Q480 324 920 348"/>
      <path d="M40 456 Q480 434 920 456"/>
      <path d="M40 552 Q480 534 920 552"/>
      <path d="M188 60 Q158 312 188 560"/>
      <path d="M352 50 Q326 312 352 572"/>
      <path d="M516 46 Q516 312 516 576"/>
      <path d="M680 50 Q706 312 680 572"/>
      <path d="M828 60 Q858 312 828 560"/>
    </g>
"""


def lead_url(country: dict) -> str:
    """Best click target when a country has no hub yet: its lead city guide."""
    if country.get("hub"):
        return country["hub"]   # relative, e.g. "countries/japan/"
    cities = country.get("cities") or []
    for city in cities:
        for pref in ("first-timers-guide", "things-to-do"):
            for g in city["guides"]:
                if pref in g["slug"]:
                    return g["url"]
        if city["guides"]:
            return city["guides"][0]["url"]
    if country.get("guides"):
        return country["guides"][0]["url"]
    return "all-guides.html"


def node_radius(guides: int) -> float:
    return round(11 + (guides ** 0.5) * 2.4, 1)   # Japan 24 -> ~23, Singapore 2 -> ~14


def build_svg(data: dict) -> str:
    by_name = {c["name"]: c for c in data["countries"]}
    nodes = []
    legend = []
    for name, (x, y) in COORDS.items():
        c = by_name.get(name)
        if not c:
            continue
        gc = c["guideCount"]
        r = node_radius(gc)
        href = lead_url(c)
        cities = [ct["name"] for ct in (c.get("cities") or [])][:3]
        cities_str = " · ".join(cities) if cities else "Guides & prep"
        aria = f"{name}: {gc} guides"
        legend.append((gc,
            f'      <li><a class="apac-chip" href="{escape(href)}">'
            f'<span class="apac-chip-name">{escape(name)}</span>'
            f'<span class="apac-chip-count">{gc}</span></a></li>'
        ))
        nodes.append(
            f'      <a class="apac-node" href="{escape(href)}" role="listitem" '
            f'aria-label="{escape(aria)}" data-country="{escape(name)}" '
            f'data-guides="{gc}" data-cities="{escape(cities_str)}">\n'
            f'        <circle class="apac-halo" cx="{x}" cy="{y}" r="{r + 10}"></circle>\n'
            f'        <circle class="apac-dot" cx="{x}" cy="{y}" r="{r}"></circle>\n'
            f'        <text class="apac-count" x="{x}" y="{y + 4.5}">{gc}</text>\n'
            f'        <text class="apac-name" x="{x}" y="{y + r + 16}">{escape(name)}</text>\n'
            f'      </a>'
        )
    nodes_svg = "\n".join(nodes)
    legend_html = "\n".join(h for _, h in sorted(legend, key=lambda t: -t[0]))

    return f"""{MARK_BEGIN}
<div class="apac-map-wrap">
  <svg class="apac-map-svg" viewBox="0 0 960 620" role="list"
       aria-label="Destinations we cover across Asia-Pacific — tap a country">
    <defs>
      <radialGradient id="apacField" cx="52%" cy="42%" r="75%">
        <stop offset="0%" stop-color="#20304c"></stop>
        <stop offset="60%" stop-color="#182338"></stop>
        <stop offset="100%" stop-color="#111a2b"></stop>
      </radialGradient>
      <pattern id="apacDots" width="26" height="26" patternUnits="userSpaceOnUse">
        <circle cx="1.5" cy="1.5" r="1.5" fill="#ffffff" opacity="0.05"></circle>
      </pattern>
      <filter id="apacGlow" x="-60%" y="-60%" width="220%" height="220%">
        <feGaussianBlur stdDeviation="7" result="b"></feGaussianBlur>
        <feMerge><feMergeNode in="b"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
      </filter>
    </defs>
    <rect class="apac-field" x="0" y="0" width="960" height="620" rx="26" fill="url(#apacField)"></rect>
{GRID}    <rect x="0" y="0" width="960" height="620" rx="26" fill="url(#apacDots)"></rect>
    <g class="apac-nodes">
{nodes_svg}
    </g>
  </svg>
  <div class="apac-tooltip" role="status" aria-live="polite" hidden>
    <span class="apac-tt-name"></span>
    <span class="apac-tt-meta"></span>
  </div>
</div>
<ul class="apac-legend" aria-label="All countries we cover">
{legend_html}
</ul>
{MARK_END}"""


def inject(html: str, block: str) -> str:
    pat = re.compile(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END), re.S)
    if pat.search(html):
        return pat.sub(lambda _: block, html)
    raise SystemExit("apac-map markers not found in index.html — add the section shell first.")


def main() -> None:
    data = json.loads((SITE / "data" / "knowledge.json").read_text(encoding="utf-8"))
    block = build_svg(data)
    n = 0
    for base in (SITE, DOCS):
        idx = base / "index.html"
        html = idx.read_text(encoding="utf-8")
        new = inject(html, block)
        if new != html:
            idx.write_text(new, encoding="utf-8")
            n += 1
    covered = [c for c in COORDS if any(k["name"] == c for k in data["countries"])]
    print(f"apac-map: {len(covered)} country nodes rendered into {n} file(s)")


if __name__ == "__main__":
    main()
