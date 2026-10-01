#!/usr/bin/env python3
"""
build_map.py — the homepage world map of the places we cover.

Renders a real world map (Equal Earth projection) into index.html between the
BEGIN/END markers. Countries with destination guides are gold and open their hub
or lead guide; countries with prep notes only (plugs & voltage, plus eSIM and
rail-pass guides where we have them) are pale gold and open those notes. Hong
Kong and Singapore are too small for the 1:110m shapes, so they are dots. A
toggle zooms to Asia-Pacific, where most of the guides are.

Country shapes: world-atlas 2.0.2 (countries-110m.json; ISC licence, Mike
Bostock), built from Natural Earth (public domain). It is a build-time input
kept out of git in data/geo/; without it the map already on the page stays.

Usage:  python build_map.py            # writes site/ + docs/ index.html
"""
from __future__ import annotations

import json
import math
import re
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"
MARK_BEGIN = "<!-- BEGIN apac-map (managed by build_map.py) -->"
MARK_END = "<!-- END apac-map -->"

GEO = REPO / "data" / "geo" / "countries-110m.json"
W = 1920                                   # drawing units across; the SVG scales to fit
LAT_MIN, LAT_MAX = -57.0, 84.0             # Tierra del Fuego to northern Greenland

# Too small for 1:110m shapes: drawn as dots (lon, lat).
DOTS = {"Hong Kong": (114.17, 22.32), "Singapore": (103.82, 1.35)}
# knowledge.json name -> world-atlas name, where they differ
ATLAS_NAME = {"United States": "United States of America"}
# Prep-only countries: travel-power slug -> world-atlas name
POWER = {
    "united-states": "United States of America", "canada": "Canada", "brazil": "Brazil",
    "united-kingdom": "United Kingdom", "france": "France", "germany": "Germany",
    "italy": "Italy", "spain": "Spain", "switzerland": "Switzerland",
    "south-africa": "South Africa", "united-arab-emirates": "United Arab Emirates",
    "india": "India", "china": "China", "new-zealand": "New Zealand",
}
DISPLAY = {"United States of America": "United States"}
# Where each guide country's name sits in the close-up (lon, lat, text-anchor).
LABEL_AT = {
    "Japan": (142.6, 35.2, "start"), "South Korea": (125.6, 36.6, "end"),
    "Taiwan": (122.4, 23.4, "start"), "Hong Kong": (113.4, 21.4, "end"),
    "Philippines": (122.5, 12.5, "start"), "Vietnam": (108.6, 14.8, "start"),
    "Thailand": (100.7, 15.6, "middle"), "Malaysia": (101.9, 4.6, "middle"),
    "Singapore": (104.6, 0.9, "start"), "Indonesia": (114.0, -5.2, "middle"),
    "Australia": (134.0, -24.0, "middle"),
}
# The close-up: Hokkaido to Bali, Myanmar's coast to Japan's Pacific side
CLOSEUP = (92.0, 46.5, 147.0, -11.5)
EUROPE = {"United Kingdom", "France", "Germany", "Italy", "Spain", "Switzerland"}
REGION = {
    "United States of America": "Americas", "Canada": "Americas", "Brazil": "Americas",
    "United Kingdom": "Europe", "France": "Europe", "Germany": "Europe", "Italy": "Europe",
    "Spain": "Europe", "Switzerland": "Europe", "South Africa": "Middle East & Africa",
    "United Arab Emirates": "Middle East & Africa", "India": "Asia", "China": "Asia",
    "New Zealand": "Asia-Pacific",
}


def _equal_earth(lon: float, lat: float) -> tuple[float, float]:
    """Equal Earth projection (Šavrič, Patterson & Jenny 2018), unit sphere."""
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    m = math.sqrt(3) / 2
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(m * math.sin(phi))
    t2, t6 = th * th, th ** 6
    x = lam * math.cos(th) / (m * (a1 + 3 * a2 * t2 + t6 * (7 * a3 + 9 * a4 * t2)))
    y = th * (a1 + a2 * t2 + t6 * (a3 + a4 * t2))
    return x, y


_XMAX = _equal_earth(180, 0)[0]
_SCALE = W / (2 * _XMAX)
_YTOP = _equal_earth(0, LAT_MAX)[1]
H = round((_YTOP - _equal_earth(0, LAT_MIN)[1]) * _SCALE)


def project(lon: float, lat: float) -> tuple[float, float]:
    x, y = _equal_earth(lon, max(min(lat, LAT_MAX), LAT_MIN))
    return (x + _XMAX) * _SCALE, (_YTOP - y) * _SCALE


def _rings(topo: dict) -> dict[str, list[list[tuple[float, float]]]]:
    """Country name -> rings of (lon, lat), decoded from the TopoJSON arcs."""
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idxs):
        out = []
        for i in idxs:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    by_name = {}
    for g in topo["objects"]["countries"]["geometries"]:
        name = g["properties"]["name"]
        polys = [g["arcs"]] if g["type"] == "Polygon" else g["arcs"] if g["type"] == "MultiPolygon" else []
        by_name[name] = [ring(r) for poly in polys for r in poly]
    return by_name


def _path(rings) -> str:
    """Relative, integer path data: small enough to inline on the homepage."""
    out = []
    for r in rings:
        # A ring that crosses the 180th meridian (Fiji, Chukotka, the Aleutians) jumps
        # across the whole map: cut it there and close each side on its own.
        pieces, pts, last = [], [], None
        for lon, lat in r:
            p = tuple(round(v) for v in project(lon, lat))
            if last is not None and abs(p[0] - last[0]) > W / 2:
                pieces.append(pts)
                pts = []
            if p != last:
                pts.append(p)
                last = p
        pieces.append(pts)
        for pts in pieces:
            if len(pts) < 3:
                continue
            cmd = [f"M{pts[0][0]} {pts[0][1]}"]
            cmd += [f"l{b[0] - a[0]} {b[1] - a[1]}" for a, b in zip(pts, pts[1:])]
            out.append("".join(cmd).replace(" -", "-") + "z")
    return "".join(out)


def _graticule() -> str:
    parts = []
    for lat in range(-30, 90, 30):
        pts = [tuple(round(v) for v in project(lon, lat)) for lon in range(-180, 181, 5)]
        parts.append("M" + "L".join(f"{x} {y}" for x, y in pts))
    for lon in range(-150, 181, 30):
        pts = [tuple(round(v) for v in project(lon, lat)) for lat in range(int(LAT_MIN), int(LAT_MAX) + 1, 3)]
        parts.append("M" + "L".join(f"{x} {y}" for x, y in pts))
    return "".join(parts)


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


def _prep_meta(atlas: str) -> str:
    notes = ["plugs & voltage"]
    if atlas == "United States of America":
        notes.append("eSIM")
    if atlas in EUROPE:
        notes += ["Europe eSIM", "rail pass"]
    return "Prep notes: " + ", ".join(notes)


def build_svg(data: dict, topo: dict) -> str:
    rings = _rings(topo)
    guides = {ATLAS_NAME.get(c["name"], c["name"]): c for c in data["countries"]}
    prep = {atlas: slug for slug, atlas in POWER.items() if atlas not in guides
            and (SITE / "travel-power" / f"{slug}.html").exists()}

    base = "".join(_path(r) for name, r in rings.items()
                   if name not in guides and name not in prep and name != "Antarctica")
    shapes, labels, legend_g, legend_p = [], [], [], []
    for atlas, c in sorted(guides.items(), key=lambda kv: -kv[1]["guideCount"]):
        gc, href = c["guideCount"], lead_url(c)
        cities = " · ".join(ct["name"] for ct in (c.get("cities") or [])[:3]) or "Guides & prep"
        attrs = (f'class="wmap-c is-guides" href="{escape(href)}" data-country="{escape(c["name"])}" '
                 f'data-meta="{gc} guides · {escape(cities)}" aria-label="{escape(c["name"])}: {gc} guides"')
        if atlas in DOTS:
            x, y = (round(v) for v in project(*DOTS[atlas]))
            shapes.append(f'      <a {attrs}><circle cx="{x}" cy="{y}" r="7"></circle></a>')
        elif atlas in rings:
            shapes.append(f'      <a {attrs}><path d="{_path(rings[atlas])}"></path></a>')
        else:
            continue
        if c["name"] in LABEL_AT:
            lon, lat, anchor = LABEL_AT[c["name"]]
            lx, ly = (round(v) for v in project(lon, lat))
            labels.append(f'      <text class="wmap-label" x="{lx}" y="{ly}" text-anchor="{anchor}">'
                          f'{escape(c["name"])}</text>')
        legend_g.append(f'      <li><a class="apac-chip" href="{escape(href)}"><span class="apac-chip-name">'
                        f'{escape(c["name"])}</span><span class="apac-chip-count">{gc}</span></a></li>')
    for atlas, slug in sorted(prep.items(), key=lambda kv: (REGION.get(kv[0], ""), kv[0])):
        name = DISPLAY.get(atlas, atlas)
        href = f"travel-power/{slug}.html"
        meta = _prep_meta(atlas)
        shapes.append(f'      <a class="wmap-c is-prep" href="{href}" data-country="{escape(name)}" '
                      f'data-meta="{escape(meta)}" aria-label="{escape(name)}: {escape(meta)}">'
                      f'<path d="{_path(rings[atlas])}"></path></a>')
        legend_p.append(f'      <li><a class="apac-chip is-prep" href="{href}"><span class="apac-chip-name">'
                        f'{escape(name)}</span></a></li>')

    # The close-up keeps the world view's shape, so the map does not jump in height
    lon0, lat0, lon1, lat1 = CLOSEUP
    x0, y0 = project(lon0, lat0)
    x1, y1 = project(lon1, lat1)
    h = y1 - y0
    w = h * W / H
    cx = min(max((x0 + x1) / 2, w / 2), W - w / 2)
    apac = f"{round(cx - w / 2)} {round(y0)} {round(w)} {round(h)}"
    # Phones have height to spare: there the close-up is the region's own shape
    corners = [project(lo, la) for lo in (lon0, lon1) for la in (lat0, lat1)]
    nx0, nx1 = min(c[0] for c in corners) - 20, max(c[0] for c in corners) + 20
    ny0, ny1 = min(c[1] for c in corners) - 10, max(c[1] for c in corners) + 10
    narrow = f"{round(nx0)} {round(ny0)} {round(nx1 - nx0)} {round(ny1 - ny0)}"
    n_g, n_p = len(legend_g), len(legend_p)
    return f"""{MARK_BEGIN}
<div class="apac-map-wrap wmap" data-world="0 0 {W} {H}" data-apac="{apac}" data-apac-narrow="{narrow}">
  <div class="wmap-views" role="group" aria-label="Map view">
    <button type="button" class="wmap-view is-on" data-view="world" aria-pressed="true">World</button>
    <button type="button" class="wmap-view" data-view="apac" aria-pressed="false">East &amp; Southeast Asia, close up</button>
  </div>
  <svg class="apac-map-svg wmap-svg" viewBox="0 0 {W} {H}" role="list"
       aria-label="Places we cover around the world — tap a country">
    <path class="wmap-grat" d="{_graticule()}"></path>
    <path class="wmap-land" d="{base}"></path>
    <g class="wmap-cs">
{chr(10).join(shapes)}
    </g>
    <g class="wmap-labels" aria-hidden="true">
{chr(10).join(labels)}
    </g>
  </svg>
  <div class="apac-tooltip" role="status" aria-live="polite" hidden>
    <span class="apac-tt-name"></span>
    <span class="apac-tt-meta"></span>
  </div>
</div>
<div class="wmap-key">
  <p class="wmap-key-h"><span class="wmap-swatch is-guides"></span>Destination guides · {n_g} places</p>
  <ul class="apac-legend" aria-label="Places with destination guides">
{chr(10).join(legend_g)}
  </ul>
  <p class="wmap-key-h"><span class="wmap-swatch is-prep"></span>Prep notes · {n_p} more countries</p>
  <ul class="apac-legend" aria-label="Countries with prep notes">
{chr(10).join(legend_p)}
  </ul>
</div>
{MARK_END}"""


def inject(html: str, block: str) -> str:
    pat = re.compile(re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END), re.S)
    if pat.search(html):
        return pat.sub(lambda _: block, html)
    raise SystemExit("apac-map markers not found in index.html — add the section shell first.")


def main() -> None:
    data = json.loads((SITE / "data" / "knowledge.json").read_text(encoding="utf-8"))
    if not GEO.exists():
        print(f"world map: {GEO.relative_to(REPO)} missing — map left as it is")
        return
    block = build_svg(data, json.loads(GEO.read_text(encoding="utf-8")))
    n = 0
    for base in (SITE, DOCS):
        idx = base / "index.html"
        html = idx.read_text(encoding="utf-8")
        new = inject(html, block)
        if new != html:
            idx.write_text(new, encoding="utf-8")
            n += 1
    print(f"world map: {len(data['countries'])} places with guides rendered into {n} file(s)")


if __name__ == "__main__":
    main()
