#!/usr/bin/env python3
"""
build_library.py

(1) Regenerate the homepage "Latest guides & essays" strip (news-release style,
    newest 12, with a "View all guides" button).
(2) Regenerate a full archive page at /all-guides.html — every published guide,
    grouped by category, self-updating.

Sources: the SLIDES registry in build_carousel.py (+ PROFILES below). Dates come
from git (first commit that added each file), so nothing needs hand-maintaining.

Runs automatically at the end of `build_carousel.py --write`; or:  python build_library.py
"""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

import site_taxonomy as T

REPO = Path(__file__).resolve().parent
MARK_BEGIN = "<!-- BEGIN library (managed by build_library.py) -->"
MARK_END = "<!-- END library -->"
HOME_SHOW = 12
GA4_ID = "G-JRGK9CN3B1"

# ── Live inventory (drives the homepage hero stats, self-updating) ──────────
# Profiles that live under articles/ but count as destinations, not guides.
PROFILES_IN_ARTICLES = {"south-korea-country-profile.html"}
# Explicit tool set, so the count is intentional rather than accidental.
TOOL_FILES = ["tools/esim-finder.html", "tools/insurance-finder.html",
              "checklist-generator.html", "rehearsal.html"]

PROFILES = [
    {"href": "countries/japan/index.html", "tag": "Country Profile",
     "title": "Japan: History, Society & Travel Prep", "img": "japan-photo"},
    {"href": "countries/vietnam/index.html", "tag": "Country Profile",
     "title": "Vietnam: History, Society & Travel Prep", "img": "vietnam-photo"},
    {"href": "countries/australia/index.html", "tag": "Country Profile",
     "title": "Australia: History, Society & Travel Prep", "img": "australia-photo"},
    {"href": "articles/south-korea-country-profile.html", "tag": "Country Profile",
     "title": "South Korea: History, Society & Travel Prep", "img": "south-korea-photo"},
    {"href": "cities/tokyo/index.html", "tag": "City Guide",
     "title": "Tokyo: A Layered City Guide", "img": "tokyo-photo"},
    {"href": "cities/tokyo/asakusa.html", "tag": "City Guide",
     "title": "Asakusa: Tokyo's Oldest District", "img": "asakusa-photo"},
]

# Granular slide/profile tag -> broad archive category.
CATEGORY_MAP = {
    "Itinerary": "Destinations & Itineraries",
    "Itineraries": "Destinations & Itineraries",
    "City Logistics": "Destinations & Itineraries",
    "Seasonal": "Destinations & Itineraries",
    "City Guide": "Destinations & Itineraries",
    "Country Profile": "Destinations & Itineraries",
    "Connectivity": "Connectivity & eSIM",
    "Travel Safety": "Insurance & Safety",
    "Packing": "Packing, Airports & Gear",
    "Carry-on Prep": "Packing, Airports & Gear",
    "Everyday Carry": "Packing, Airports & Gear",
    "Sun & Beach": "Packing, Airports & Gear",
    "Hotel Stay Comfort": "Packing, Airports & Gear",
    "Flight Comfort": "Packing, Airports & Gear",
    "Travel Prep": "Packing, Airports & Gear",
    "Tours & Activities": "Booking, Rail & Tours",
    "Japan Rail": "Booking, Rail & Tours",
    "Coastal Travel": "Booking, Rail & Tours",
    "Cross-Cultural Etiquette": "Culture & Language",
    "Language & Culture": "Culture & Language",
}
DEFAULT_CATEGORY = "More guides"
CATEGORY_ORDER = [
    "Destinations & Itineraries", "Connectivity & eSIM", "Insurance & Safety",
    "Packing, Airports & Gear", "Booking, Rail & Tours", "Culture & Language",
    DEFAULT_CATEGORY,
]

# The shared blocks, so the archive never carries a second, stale nav or footer.
from add_global_nav import block as _nav_block
from add_footer import block as _footer_block
NAV = _nav_block("")

GA4 = f"""<!-- BEGIN GA4 (managed by add_ga4.py) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_ID}', {{ anonymize_ip: true }});
</script>
<!-- END GA4 -->"""

DRIVE = """<script nowprocket data-noptimize="1" data-cfasync="false" data-wpfc-render="false" seraph-accel-crit="1" data-no-defer="1">
  (function () { var s=document.createElement("script"); s.async=1;
    s.src='https://tpembars.com/NTQzNzE5.js?t=543719'; document.head.appendChild(s); })();
</script>"""

FOOTER = _footer_block("")


def added_date(rel_href: str) -> str:
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ad", "--date=format:%Y.%m.%d",
         "--", f"site/{rel_href}"],
        capture_output=True, text=True, cwd=REPO).stdout.strip().splitlines()
    return out[-1] if out else date.today().strftime("%Y.%m.%d")


def first_photo(soup: BeautifulSoup) -> str:
    """The page's own first photograph, as a root-relative src (or "").

    Thumbnails used to be the Pinterest pins — posters with the title and a
    "Read the guide" button baked in. Every article now carries real photos,
    so the thumbnail is simply the first of them.
    """
    photos = all_photos(soup)
    return photos[0] if photos else ""


def all_photos(soup: BeautifulSoup) -> list[str]:
    out = []
    for img in soup.select("section.article figure img, main figure img"):
        src = img.get("src") or ""
        if not src:
            continue
        if "images.pexels.com" in src:
            src = src.split("?")[0] + "?auto=compress&cs=tinysrgb&w=480&h=320&fit=crop&dpr=2"
        else:
            src = src.replace("../", "")
        if src not in out:
            out.append(src)
    return out


def distinct_thumbs(rows: list[dict]) -> list[dict]:
    """Rows with thumbnails re-picked so no picture appears twice in one list
    (two packing guides open with the same stock photo)."""
    used, out = set(), []
    for r in rows:
        pick = next((ph for ph in r.get("photos", []) if ph not in used), r["thumb"])
        used.add(pick)
        out.append({**r, "thumb": pick})
    return out


def page_row(rel: str) -> dict:
    soup = BeautifulSoup((REPO / "site" / rel).read_text(encoding="utf-8"), "html.parser")
    h1 = soup.select_one("header h1") or soup.find("h1")
    title = " ".join(h1.get_text(" ", strip=True).split()) if h1 else Path(rel).stem
    if rel in T.PAGE_LABEL:
        tag = T.PAGE_LABEL[rel]
    else:
        lab = soup.select_one("header .label")
        tag = T.label_for(Path(rel).stem, lab.get_text(" ", strip=True) if lab else "")
    return {"href": rel, "title": title, "tag": tag, "thumb": first_photo(soup),
            "photos": all_photos(soup),
            "date": added_date(rel), "cat": T.section_for(tag)}


def build_rows() -> list[dict]:
    """Every article on disk plus the destination hubs — nothing hand-kept.

    The old registry had drifted 41 guides behind the files, so the archive
    silently left out the whole where-to-book series among others.
    """
    rels = [f"articles/{p.name}" for p in sorted((REPO / "site" / "articles").glob("*.html"))]
    rels += [r for r in T.PAGE_LABEL if (REPO / "site" / r).exists()]
    rows = [page_row(r) for r in rels]
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def row_html(r: dict, rank: int | None = None) -> str:
    img = (f'<img class="gy-lib-thumb" src="{r["thumb"]}" alt="" loading="lazy" '
           f'decoding="async" data-pin-nopin="true" />') if r["thumb"] else ""
    lead = (f'<span class="gy-lib-date gy-lib-rank">{rank}</span>' if rank
            else f'<span class="gy-lib-date">{r["date"]}</span>')
    return (f'<a class="gy-lib-row" href="{r["href"]}">{lead}'
            f'<span class="gy-lib-body"><span class="gy-lib-tag">{r["tag"]}</span>'
            f'<span class="gy-lib-title">{r["title"]}</span></span>{img}</a>')


HOME_POPULAR = 7
POP_CSV = REPO / "data" / "popular_pages.csv"


def popular_pick(rows: list[dict]) -> list[dict]:
    """Top HOME_POPULAR registry pages by real 28-day traffic (rank_popular.py).

    Only pages present in the SLIDES/PROFILES registry render (we need title,
    tag and thumb); missing csv -> [] and the caller falls back to newest.
    """
    if not POP_CSV.exists():
        return []
    by_href = {r["href"]: r for r in rows}
    import csv as _csv
    picked = []
    with POP_CSV.open() as f:
        for line in _csv.DictReader(f):
            r = by_href.get(line["path"])
            if r:
                picked.append(r)
            if len(picked) == HOME_POPULAR:
                break
    return picked


def pop_window() -> str:
    """'Data: 26 Aug – 22 Sep 2026.' from the csv header, or '' if unknown."""
    if not POP_CSV.exists():
        return ""
    head = POP_CSV.read_text(encoding="utf-8").splitlines()[0]
    m = re.search(r"# (\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", head)
    if not m:
        return ""
    a, b = (date.fromisoformat(x) for x in m.groups())
    return f"Data: {a.day} {a:%b} \u2013 {b.day} {b:%b %Y}."


LATEST_BEGIN = "<!-- BEGIN latest (managed by build_library.py) -->"
LATEST_END = "<!-- END latest -->"
LATEST_SHOW = 6


def render_latest(rows: list[dict], total: int) -> str:
    """Newest guides that have a real photo, as an even grid of cards."""
    picks = distinct_thumbs([r for r in rows if r["thumb"] and r["href"].startswith("articles/")][:LATEST_SHOW])
    cards = "\n".join(
        f'    <a class="gy-card" href="{r["href"]}">'
        f'<img class="gy-card-img" src="{r["thumb"]}" alt="" loading="lazy" decoding="async" data-pin-nopin="true" />'
        f'<span class="gy-card-tag">{r["tag"]}</span>'
        f'<span class="gy-card-title">{r["title"]}</span></a>'
        for r in picks)
    return (f"{LATEST_BEGIN}\n"
            '<section class="gy-latest" id="guides">\n'
            '  <div class="gy-section-head"><h2>New on Gently Yonder</h2>'
            f'<a class="gy-section-more" href="all-guides.html">All {total} guides &rarr;</a></div>\n'
            f'  <div class="gy-card-grid">\n{cards}\n  </div>\n'
            "</section>\n"
            f"{LATEST_END}")


RANK_STYLE = ('  <style>.gy-lib-rank{font-family:Georgia,"Times New Roman",serif;'
              'font-size:1.5rem;font-weight:700;color:#B8945F;font-variant-numeric:'
              'tabular-nums}</style>')


def render_home(rows: list[dict]) -> str:
    pop = distinct_thumbs(popular_pick(rows))
    if len(pop) >= 5:
        body = "\n".join(row_html(r, rank=i + 1) for i, r in enumerate(pop))
        head = "  <h2>Most read this month</h2>\n"
        intro = ('  <p class="intro">What readers are actually opening — ranked by search '
                 "clicks and visits from search, AI assistants and links, excluding our own "
                 f"traffic. {pop_window()}</p>\n" + RANK_STYLE + "\n")
    else:
        body = "\n".join(row_html(r) for r in rows[:HOME_SHOW])
        head = "  <h2>Latest guides &amp; essays</h2>\n"
        intro = ('  <p class="intro">Everything we publish, newest first — '
                 "the carousel below draws from the same pool.</p>\n")
    return (f"{MARK_BEGIN}\n"
            '<section class="gy-library" id="profiles" data-reveal>\n'
            + head + intro +
            f'  <div class="gy-lib-list">\n{body}\n  </div>\n'
            '  <a class="gy-lib-more" href="all-guides.html">View all guides by category &rarr;</a>\n'
            "</section>\n"
            f"{MARK_END}")


def render_archive(rows: list[dict]) -> str:
    by_cat: dict[str, list[dict]] = {}
    for r in rows:
        by_cat.setdefault(r["cat"], []).append(r)
    sections = []
    for cat in T.SECTION_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        lis = "\n".join(row_html(r) for r in items)
        anchor = re.sub(r"[^a-z]+", "-", cat.lower()).strip("-")
        sections.append(f'<section class="gy-arch-cat" id="{anchor}">\n'
                        f'  <h2>{cat} <span class="gy-arch-count">{len(items)}</span></h2>\n'
                        f'  <div class="gy-lib-list">\n{lis}\n  </div>\n</section>')
    body = "\n".join(sections)
    total = len(rows)
    title = "All Guides & Essays — Gently Yonder"
    desc = ("Every Gently Yonder travel-prep guide and essay, organised by category — "
            "itineraries, eSIMs, insurance, packing, booking, and culture.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="https://gentlyyonder.com/all-guides.html" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:url" content="https://gentlyyonder.com/all-guides.html" />
<meta property="og:site_name" content="Gently Yonder" />
<link rel="stylesheet" href="style-v2.css" />
{GA4}
<!-- BEGIN favicon (managed by add_favicon.py) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="icon" href="/favicon-48.png" type="image/png" sizes="48x48"/>
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<!-- END favicon -->
{DRIVE}
</head>
<body>
{NAV}
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol><li><a href="index.html">Gently Yonder</a></li><li aria-current="page">All guides</li></ol>
</nav>
<header class="gy-arch-head">
<div class="gy-arch-head-inner">
<p class="label">The library</p>
<h1>All guides &amp; essays</h1>
<p>Every guide we've published, by category — {total} and counting. Calm, careful
travel preparation, from eSIMs to itineraries.</p>
</div>
</header>
<main class="gy-archive">
{body}
<p class="back-link"><a href="index.html">&larr; Back to Gently Yonder</a></p>
</main>
{FOOTER}
<script defer src="js/gy-reveal.js"></script>
<script src="js/email-popup.js" data-root="" defer></script>
</body>
</html>
"""


def inventory() -> dict:
    """Count what actually exists on disk — the single source of truth."""
    arts = sorted((REPO / "site" / "articles").glob("*.html"))
    guides = [p for p in arts if p.name not in PROFILES_IN_ARTICLES]
    dests = (sorted((REPO / "site" / "countries").glob("*/index.html"))
             + sorted((REPO / "site" / "cities").glob("*/*.html"))
             + [REPO / "site" / "articles" / n for n in sorted(PROFILES_IN_ARTICLES)
                if (REPO / "site" / "articles" / n).exists()])
    tools = [f for f in TOOL_FILES if (REPO / "site" / f).exists()]
    total = sum(1 for _ in (REPO / "site").rglob("*.html"))
    return {"guides": len(guides), "destinations": len(dests),
            "tools": len(tools), "total_pages": total}


def update_hero(counts: dict) -> None:
    """Write the live counts into the homepage hero stats (site + docs)."""
    pairs = [("travel guides", counts["guides"]),
             ("destination guides", counts["destinations"]),
             ("free tools", counts["tools"])]
    for base in ("site", "docs"):
        p = REPO / base / "index.html"
        t = orig = p.read_text(encoding="utf-8")
        for label, n in pairs:
            t = re.sub(r'data-count-to="\d+">\d+</span>' + re.escape(label),
                       f'data-count-to="{n}">{n}</span>{label}', t)
        if t != orig:
            p.write_text(t, encoding="utf-8")


def main() -> None:
    rows = build_rows()
    home = render_home(rows)
    n_pop = len(popular_pick(rows))
    strip_desc = (f"most-read {min(n_pop, HOME_POPULAR)}" if n_pop >= 5
                  else f"newest {min(HOME_SHOW, len(rows))}")
    for base in ("site", "docs"):
        # homepage strip
        p = REPO / base / "index.html"
        t = p.read_text(encoding="utf-8")
        if MARK_BEGIN in t:
            s = t.index(MARK_BEGIN); e = t.index(MARK_END) + len(MARK_END)
            t = t[:s] + home + t[e:]
        if LATEST_BEGIN in t:
            s = t.index(LATEST_BEGIN); e = t.index(LATEST_END) + len(LATEST_END)
            t = t[:s] + render_latest(rows, inventory()["guides"]) + t[e:]
        p.write_text(t, encoding="utf-8")
        # full archive page
        (REPO / base / "all-guides.html").write_text(render_archive(rows), encoding="utf-8")
    _add_to_sitemap()
    counts = inventory()
    update_hero(counts)
    print(f"  library refreshed — home strip ({strip_desc}) + "
          f"all-guides.html ({len(rows)} guides)")
    print(f"  inventory (live, from files) — {counts['guides']} travel guides, "
          f"{counts['destinations']} destination guides, {counts['tools']} tools "
          f"| {counts['total_pages']} total pages")


def _add_to_sitemap() -> None:
    url = "https://gentlyyonder.com/all-guides.html"
    for p in (REPO / "site" / "sitemap.xml", REPO / "docs" / "sitemap.xml"):
        s = p.read_text(encoding="utf-8")
        if url in s:
            continue
        block = (f"  <url>\n    <loc>{url}</loc>\n    <changefreq>weekly</changefreq>\n"
                 f"    <priority>0.7</priority>\n  </url>\n")
        p.write_text(s.replace("</urlset>", block + "</urlset>"), encoding="utf-8")


if __name__ == "__main__":
    main()
