"""City hubs and place breadcrumbs (2026-11-19, competitor study: Travel Lemming and Earth Trekkers
file every guide under a destination, "Home > France > Paris", and give each city one page).

For every city with a base stay guide (where-to-stay-in-<city>) and at least MIN_GUIDES guides about
it, this writes places/<city>.html (site + docs): the city's stay guides, tickets/tours/car hire, and
everything else, as photo cards. Each of those guides then gets the breadcrumb
"Gently Yonder > <City> > <title>" (HTML and BreadcrumbList JSON-LD) instead of "Guides".
A guide is filed under a city by its slug (the city's words, e.g. ...-paris-christmas) or by EXTRA
for pages named after a sight (the Colosseum -> Rome). Idempotent; run by ops/pipeline.sh.

usage: .venv/bin/python ops/place_hubs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import build_library as L  # noqa: E402

MIN_GUIDES = 3
ROOTS = (REPO / "site", REPO / "docs")
# pages named after a sight or event rather than the city
EXTRA = {
    "where-to-buy-colosseum-tickets": "rome", "where-to-buy-vatican-museums-tickets": "rome",
    "where-to-buy-disneyland-paris-tickets": "paris", "where-to-stay-for-disneyland-paris": "paris",
    "where-to-buy-tokyo-disney-resort-tickets": "tokyo", "where-to-stay-for-tokyo-disney-resort": "tokyo",
    "where-to-buy-teamlab-planets-tickets": "tokyo", "where-to-stay-for-tokyo-marathon": "tokyo",
    "where-to-buy-universal-studios-japan-tickets": "osaka", "where-to-stay-for-universal-studios-japan": "osaka",
    "where-to-buy-burj-khalifa-tickets": "dubai", "where-to-buy-universal-orlando-tickets": "orlando",
    "where-to-stay-for-london-marathon": "london", "where-to-stay-for-wimbledon": "london",
    "where-to-stay-for-boston-marathon": "boston", "where-to-stay-for-keukenhof": "amsterdam",
    "car-rental-iceland": "reykjavik", "car-rental-new-zealand-south-island": "queenstown",
}
NAMES = {"new-york": "New York", "hong-kong": "Hong Kong", "kuala-lumpur": "Kuala Lumpur",
         "las-vegas": "Las Vegas", "los-angeles": "Los Angeles", "san-francisco": "San Francisco",
         "san-diego": "San Diego", "mexico-city": "Mexico City", "cape-town": "Cape Town",
         "ho-chi-minh-city": "Ho Chi Minh City", "da-nang": "Da Nang", "chiang-mai": "Chiang Mai",
         "washington-dc": "Washington, DC", "new-orleans": "New Orleans", "rio": "Rio de Janeiro"}


def cities() -> list[str]:
    """City slugs that have a base stay guide (no event suffix)."""
    slugs = sorted(p.stem[len("where-to-stay-in-"):] for p in (REPO / "site" / "articles").glob("where-to-stay-in-*.html"))
    return [s for s in slugs if not any(o != s and s.startswith(o + "-") for o in slugs)]


def place_of(slug: str, cs: list[str]) -> str | None:
    if slug in EXTRA:
        return EXTRA[slug]
    hits = [c for c in cs if re.search(rf"(^|-){re.escape(c)}(-|$)", slug)]
    hits.sort(key=lambda c: (c != "japan", len(c)), reverse=True)   # a city before the country; "new-york" before "york"
    return hits[0] if hits else None


def name_of(c: str) -> str:
    return NAMES.get(c, c.replace("-", " ").title())


GROUPS = [("Where to stay", lambda r: r["tag"] == "Stay"),
          ("Tickets, tours and car hire", lambda r: r["tag"] == "Booking & tours"),
          ("Before you go, and more", lambda r: r["tag"] not in ("Stay", "Booking & tours"))]


def render(c: str, rows: list[dict]) -> str:
    name = name_of(c)
    url = f"https://gentlyyonder.com/places/{c}.html"
    secs = []
    for title, keep in GROUPS:
        items = [r for r in rows if keep(r)]
        if c and title == "Where to stay":            # the city's own guide first
            items.sort(key=lambda r: (r["href"] != f"articles/where-to-stay-in-{c}.html", r["title"]))
        if not items:
            continue
        cards = "\n".join(L.pcard("../" + r["href"], r["thumb"] if r["thumb"].startswith("http") or not r["thumb"]
                                  else "../" + r["thumb"], L.short_title(r["title"]), w=320) for r in items)
        secs.append(f'<section class="gy-arch-cat">\n  <h2>{title} <span class="gy-arch-count">{len(items)}</span></h2>\n'
                    f'  <div class="gy-pgrid gy-pgrid--hub">\n{cards}\n  </div>\n</section>')
    ld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "url": url,
                     "name": f"{name}: our guides",
                     "isPartOf": {"@type": "WebSite", "name": "Gently Yonder", "url": "https://gentlyyonder.com/"}})
    bc = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Gently Yonder", "item": "https://gentlyyonder.com/"},
        {"@type": "ListItem", "position": 2, "name": name}]})
    desc = (f"Every Gently Yonder guide to {name} in one place: where to stay, for which dates and events, "
            f"where to buy tickets, and how to get around.")[:160]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{name}: Where to Stay, Tickets and Getting Around | Gently Yonder</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{url}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<link rel="stylesheet" href="../style-v2.css" />
<script type="application/ld+json">{ld}</script>
<script type="application/ld+json">{bc}</script>
{L.GA4}
<!-- BEGIN favicon (managed by add_favicon.py) -->
<link href="/favicon.svg" rel="icon" type="image/svg+xml"/>
<link href="/favicon-48.png" rel="icon" sizes="48x48" type="image/png"/>
<link href="/favicon-192.png" rel="icon" sizes="192x192" type="image/png"/>
<link href="/apple-touch-icon.png" rel="apple-touch-icon"/>
<!-- END favicon -->
</head>
<body>
{L._nav_block("../")}
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol><li><a href="../index.html">Gently Yonder</a></li><li aria-current="page">{name}</li></ol>
</nav>
<header class="gy-arch-head">
<div class="gy-arch-head-inner">
<p class="label">Destination</p>
<h1>{name}</h1>
<p>Everything we have published on {name}, in one place: where to stay and for which dates, where to
buy tickets, and how to get around. Start with the area guide, then the page for your dates.</p>
</div>
</header>
<main class="gy-archive" id="main">
{chr(10).join(secs)}
<p class="back-link"><a href="../all-guides.html">&larr; All guides</a></p>
</main>
{L._footer_block("../")}
<script defer src="../js/gy-reveal.js"></script>
<script src="../js/email-popup.js" data-root="../" defer></script>
</body>
</html>
"""


CRUMB_RE = re.compile(r'(<nav aria-label="Breadcrumb" class="breadcrumb">\s*<ol>\s*<li><a href="\.\./index\.html">Gently Yonder</a></li>\s*)'
                      r'<li><a href="[^"]*">[^<]*</a></li>')
LD_RE = re.compile(r'("position": 2,\s*"name": )"[^"]*"(,\s*"item": )"[^"]*"')


def crumb(page: str, c: str) -> str:
    name = name_of(c)
    page = CRUMB_RE.sub(lambda m: m.group(1) + f'<li><a href="../places/{c}.html">{name}</a></li>', page, count=1)
    return LD_RE.sub(lambda m: m.group(1) + json.dumps(name) + m.group(2) + f'"https://gentlyyonder.com/places/{c}.html"',
                     page, count=1)


def main() -> None:
    cs = cities()
    by: dict[str, list[str]] = {}
    for p in sorted((REPO / "site" / "articles").glob("*.html")):
        if L._noindex(p):
            continue
        c = place_of(p.stem, cs)
        if c:
            by.setdefault(c, []).append(p.name)
    hubs = {c: names for c, names in by.items() if len(names) >= MIN_GUIDES}
    for c, names in hubs.items():
        rows = [L.page_row(f"articles/{n}") for n in names]
        html = render(c, rows)
        for root in ROOTS:
            out = root / "places" / f"{c}.html"
            out.parent.mkdir(exist_ok=True)
            if not out.exists() or out.read_text(encoding="utf-8") != html:
                out.write_text(html, encoding="utf-8")
        for n in names:
            for root in ROOTS:
                f = root / "articles" / n
                t = f.read_text(encoding="utf-8")
                new = crumb(t, c)
                if new != t:
                    f.write_text(new, encoding="utf-8")
    for root in ROOTS:                                  # sitemap
        p = root / "sitemap.xml"
        s = p.read_text(encoding="utf-8")
        for c in hubs:
            url = f"https://gentlyyonder.com/places/{c}.html"
            if f"<loc>{url}</loc>" not in s:
                s = s.replace("</urlset>", f"  <url>\n    <loc>{url}</loc>\n    <changefreq>weekly</changefreq>\n"
                                           f"    <priority>0.7</priority>\n  </url>\n</urlset>")
        p.write_text(s, encoding="utf-8")
    print(f"place hubs: {len(hubs)} ({', '.join(sorted(hubs))}); guides filed: {sum(map(len, hubs.values()))}")


if __name__ == "__main__":
    main()
