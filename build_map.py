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


# --- the globe: land as dots, the cities we cover, the places readers fly from ------
# Each city with guides: (lat, lng, the airport code to search flights to, a note when
# that airport is not in the city). Centres are approximate; distances are shown
# rounded to 100 km, which is well inside that error.
CITY_INFO = {
    "Tokyo": (35.68, 139.76, "TYO", None), "Kyoto": (35.01, 135.77, "OSA", "Osaka's airports are the nearest"),
    "Osaka": (34.69, 135.50, "OSA", None), "Seoul": (37.57, 126.98, "SEL", None),
    "Taipei": (25.03, 121.57, "TPE", None), "Hong Kong": (22.32, 114.17, "HKG", None),
    "Bangkok": (13.76, 100.50, "BKK", None), "Chiang Mai": (18.79, 98.98, "CNX", None),
    "Phuket": (7.88, 98.39, "HKT", None), "Hanoi": (21.03, 105.85, "HAN", None),
    "Ho Chi Minh City": (10.78, 106.70, "SGN", None),
    "Hoi An": (15.88, 108.33, "DAD", "Da Nang is the nearest airport"),
    "Singapore": (1.35, 103.82, "SIN", None), "Kuala Lumpur": (3.14, 101.69, "KUL", None),
    "Penang": (5.41, 100.33, "PEN", None), "Bali": (-8.65, 115.22, "DPS", None),
    "Yogyakarta": (-7.80, 110.36, "YIA", None), "Manila": (14.60, 120.98, "MNL", None),
    "Cebu": (10.32, 123.89, "CEB", None), "Sydney": (-33.87, 151.21, "SYD", None),
    "Melbourne": (-37.81, 144.96, "MEL", None), "Perth": (-31.95, 115.86, "PER", None),
}
# Where readers fly from: (code, name, lat, lng, time zones that suggest it)
ORIGINS = [
    ("LON", "London", 51.51, -0.13, ["Europe/London", "Europe/Dublin"]),
    ("PAR", "Paris", 48.86, 2.35, ["Europe/Paris", "Europe/Brussels", "Europe/Madrid"]),
    ("FRA", "Frankfurt", 50.11, 8.68, ["Europe/Berlin", "Europe/Vienna", "Europe/Zurich"]),
    ("AMS", "Amsterdam", 52.37, 4.90, ["Europe/Amsterdam"]),
    ("DXB", "Dubai", 25.20, 55.27, ["Asia/Dubai"]),
    ("DEL", "Delhi", 28.61, 77.21, ["Asia/Kolkata", "Asia/Calcutta"]),
    ("NYC", "New York", 40.71, -74.01, ["America/New_York", "America/Detroit"]),
    ("CHI", "Chicago", 41.88, -87.63, ["America/Chicago"]),
    ("LAX", "Los Angeles", 34.05, -118.24, ["America/Los_Angeles"]),
    ("SFO", "San Francisco", 37.77, -122.42, []),
    ("YTO", "Toronto", 43.65, -79.38, ["America/Toronto"]),
    ("YVR", "Vancouver", 49.28, -123.12, ["America/Vancouver"]),
    ("TYO", "Tokyo", 35.68, 139.76, ["Asia/Tokyo"]),
    ("OSA", "Osaka", 34.69, 135.50, []),
    ("SEL", "Seoul", 37.57, 126.98, ["Asia/Seoul"]),
    ("HKG", "Hong Kong", 22.32, 114.17, ["Asia/Hong_Kong"]),
    ("SIN", "Singapore", 1.35, 103.82, ["Asia/Singapore"]),
    ("BKK", "Bangkok", 13.76, 100.50, ["Asia/Bangkok"]),
    ("SYD", "Sydney", -33.87, 151.21, ["Australia/Sydney", "Australia/Brisbane"]),
    ("MEL", "Melbourne", -37.81, 144.96, ["Australia/Melbourne"]),
    ("AKL", "Auckland", -36.85, 174.76, ["Pacific/Auckland"]),
]
ESIM = {"Japan": "best-esim-japan-2026", "South Korea": "best-esim-south-korea-2026",
        "Thailand": "best-esim-thailand-2026", "Vietnam": "best-esim-vietnam-2026",
        "Taiwan": "best-esim-taiwan-2026", "Australia": "best-esim-australia-2026"}
DOT_STEP = 1.6                              # degrees between land dots, evenly spread on the sphere


def _inside(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    hit = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def globe_data(data: dict, topo: dict) -> dict:
    """Land dots coloured by what we cover, plus cities, origins and their links."""
    import stay22
    rings = _rings(topo)
    guides = {ATLAS_NAME.get(c["name"], c["name"]) for c in data["countries"]}
    prep = {atlas for slug, atlas in POWER.items() if atlas not in guides
            and (SITE / "travel-power" / f"{slug}.html").exists()}
    shapes = []                                  # (cls, bbox, rings) with the 180th meridian unwrapped
    for name, rs in rings.items():
        if name == "Antarctica":
            continue
        cls = 1 if name in guides else 2 if name in prep else 0
        for r in rs:
            lons = [p[0] for p in r]
            if max(lons) - min(lons) > 180:     # crosses the 180th meridian
                r = [(lo + 360 if lo < 0 else lo, la) for lo, la in r]
            lo0, lo1 = min(p[0] for p in r), max(p[0] for p in r)
            la0, la1 = min(p[1] for p in r), max(p[1] for p in r)
            shapes.append((cls, (lo0, lo1, la0, la1), r))
    dots = []
    lat = -56.0
    while lat <= 83.0:
        step = DOT_STEP / max(math.cos(math.radians(lat)), 0.05)
        lon = -180.0 + step / 2
        while lon < 180.0:
            for cls, (lo0, lo1, la0, la1), r in shapes:
                if not (la0 <= lat <= la1):
                    continue
                for L in (lon, lon + 360):
                    if lo0 <= L <= lo1 and _inside(L, lat, r):
                        dots += [round(lon * 10), round(lat * 10), cls]
                        break
                else:
                    continue
                break
            lon += step
        lat += DOT_STEP
    cities = []
    for c in data["countries"]:
        for ct in c.get("cities") or []:
            if ct["name"] not in CITY_INFO:
                continue
            la, lo, code, note = CITY_INFO[ct["name"]]
            slugs = {g["slug"]: g["url"] for g in ct["guides"]}
            pick = lambda key: next((u for sl, u in slugs.items() if key in sl), None)
            stay = f"where-to-stay-in-{ct['slug']}"
            links = {
                "stay": f"articles/{stay}.html" if stay in stay22.PAGES else None,
                "first": pick("first-timers-guide"), "todo": pick("things-to-do"),
                "hub": ct.get("hub"),
                "esim": f"articles/{ESIM.get(c['name'], 'best-travel-esim-2026')}.html",
                "hotels": None if stay in stay22.PAGES else stay22.area_rates(la, lo),
            }
            cities.append({"name": ct["name"], "country": c["name"], "lat": la, "lng": lo,
                           "guides": len(ct["guides"]), "iata": code, "note": note,
                           "links": {k: v for k, v in links.items() if v}})
    return {"dots": dots, "cities": cities,
            "origins": [{"code": o[0], "name": o[1], "lat": o[2], "lng": o[3], "tz": o[4]} for o in ORIGINS],
            "marker": "743846"}


GLOBE_PAGES = [SITE / "globe.html", DOCS / "globe.html"]
GLOBE_APP = ("<!-- BEGIN globe-app (managed by build_map.py) -->", "<!-- END globe-app -->")
GLOBE_INDEX = ("<!-- BEGIN globe-index (managed by build_map.py) -->", "<!-- END globe-index -->")


def _globe_markup(attrs: str = "") -> str:
    """The globe and its panel; js/globe.js brings it to life (the homepage and globe.html share it)."""
    return f"""  <div class="gy-globe" data-src="data/globe.json"{attrs} hidden>
    <div class="gy-globe-stage">
      <canvas role="img" aria-label="A globe of the places we cover. Drag to turn it; the list beside it does the same job."></canvas>
      <div class="gy-globe-zoom"><button type="button" data-zoom="in" aria-label="Zoom in">+</button><button type="button" data-zoom="out" aria-label="Zoom out">&minus;</button></div>
      <p class="gy-globe-hint">Drag to turn the globe. Tap a gold dot for that city.</p>
    </div>
    <div class="gy-globe-panel">
      <div class="gy-globe-fields">
        <label class="gy-globe-field"><span>Flying from</span><select class="gy-globe-from"></select></label>
        <label class="gy-globe-field"><span>Around</span><input class="gy-globe-date" type="date"></label>
      </div>
      <div class="gy-globe-card" hidden></div>
      <p class="gy-globe-list-h">Where our guides go, nearest first</p>
      <ol class="gy-globe-list"></ol>
      <p class="gy-globe-note">Distances are great-circle, between city centres, rounded to 100 km. Flight links open Aviasales, and hotel links Stay22, both our partners; we may earn a commission if you book, at no extra cost to you.</p>
    </div>
  </div>
"""


def _globe_index(data: dict) -> str:
    """Every place on the globe as plain links: for search engines, and for readers without JavaScript."""
    import stay22
    regions: dict[str, list[str]] = {}
    for c in sorted(data["countries"], key=lambda c: -c["guideCount"]):
        cities = []
        for ct in c.get("cities") or []:
            stay = f"where-to-stay-in-{ct['slug']}"
            href = (f"articles/{stay}.html" if stay in stay22.PAGES else ct.get("hub")
                    or (ct["guides"][0]["url"] if ct["guides"] else None))
            cities.append(f'<a href="{escape(href)}">{escape(ct["name"])}</a>' if href else escape(ct["name"]))
        regions.setdefault(c.get("region") or "Asia-Pacific", []).append(
            f'      <li><a class="gy-gi-country" href="{escape(lead_url(c))}">{escape(c["name"])}</a> '
            f'<span class="gy-gi-n">{c["guideCount"]} guides</span>'
            + (f'<span class="gy-gi-cities">{", ".join(cities)}</span>' if cities else "") + "</li>")
    guides = {ATLAS_NAME.get(c["name"], c["name"]) for c in data["countries"]}
    prep = [(DISPLAY.get(a, a), slug, a) for slug, a in POWER.items() if a not in guides
            and (SITE / "travel-power" / f"{slug}.html").exists()]
    out = ['<div class="gy-globe-index">']
    for region, items in regions.items():
        out += [f'  <div class="gy-gi-region"><h3>{escape(region)}</h3>', '    <ul>'] + items + ['    </ul>', '  </div>']
    out += ['  <div class="gy-gi-region"><h3>Prep notes</h3>', '    <ul>']
    for n, slug, atlas in sorted(prep):
        notes = ", ".join(f'<a href="{href}">{label}</a>' for label, href in _prep_links(atlas, slug))
        out.append(f'      <li><a class="gy-gi-country" href="travel-power/{slug}.html">{escape(n)}</a>'
                   f'<span class="gy-gi-cities">{notes}</span></li>')
    out += ['    </ul>', '  </div>', '</div>']
    return "\n".join(out)


def _swap(html: str, marks: tuple[str, str], block: str) -> str:
    pat = re.compile(re.escape(marks[0]) + r".*?" + re.escape(marks[1]), re.S)
    return pat.sub(lambda _: f"{marks[0]}\n{block}\n{marks[1]}", html) if pat.search(html) else html


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


def _prep_links(atlas: str, slug: str) -> list[tuple[str, str]]:
    """The notes a prep-only country has, as (label, href) from the site root; only pages that exist."""
    links = [("Plugs and voltage", f"travel-power/{slug}.html")]
    if atlas == "United States of America":
        links.append(("eSIM", "articles/best-esim-usa-2026.html"))
    if atlas in EUROPE:
        links += [("Europe eSIM", "articles/best-esim-europe-2026.html"),
                  ("Rail pass", "articles/europe-rail-pass-worth-it-2026.html")]
    return [(label, href) for label, href in links if (SITE / href).exists()]


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
    <button type="button" class="wmap-view" data-view="globe" aria-pressed="false" hidden>Globe</button>
    <button type="button" class="wmap-view is-on" data-view="world" aria-pressed="true">Flat map</button>
    <button type="button" class="wmap-view" data-view="apac" aria-pressed="false">East &amp; Southeast Asia, close up</button>
    <a class="wmap-full" href="globe.html">Open the globe full screen &rarr;</a>
  </div>
{_globe_markup()}  <svg class="apac-map-svg wmap-svg" viewBox="0 0 {W} {H}" role="list"
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
<script defer src="js/globe.js"></script>
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
    stamp = re.search(r'js/globe\.js\?v=[0-9a-f]+', html)      # keep bust_assets' version stamp
    if stamp:
        block = block.replace('src="js/globe.js"', f'src="{stamp.group(0)}"')
    if pat.search(html):
        return pat.sub(lambda _: block, html)
    raise SystemExit("apac-map markers not found in index.html — add the section shell first.")


def main() -> None:
    data = json.loads((SITE / "data" / "knowledge.json").read_text(encoding="utf-8"))
    if not GEO.exists():
        print(f"world map: {GEO.relative_to(REPO)} missing — map left as it is")
        return
    topo = json.loads(GEO.read_text(encoding="utf-8"))
    block = build_svg(data, topo)
    globe = json.dumps(globe_data(data, topo), ensure_ascii=False, separators=(",", ":"))
    for page in GLOBE_PAGES:                     # the full-page globe
        if page.exists():
            html = page.read_text(encoding="utf-8")
            new = _swap(html, GLOBE_APP, _globe_markup(' data-theme="night" data-fit="fill" data-gestures="on"').rstrip("\n"))
            new = _swap(new, GLOBE_INDEX, _globe_index(data))
            if new != html:
                page.write_text(new, encoding="utf-8")
    for base in (SITE, DOCS):
        out = base / "data" / "globe.json"
        if not out.exists() or out.read_text(encoding="utf-8") != globe:
            out.write_text(globe, encoding="utf-8")
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
