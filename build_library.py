#!/usr/bin/env python3
"""
build_library.py

Regenerate the homepage "Latest guides & essays" library — a news-release
style list (date · category · title · photo thumbnail) that always reflects
what's actually published. Sources:
  * the SLIDES registry in build_carousel.py (articles + their pin images)
  * the PROFILES list below (country/city profile pages that aren't slides)
Dates come from git (first commit that added each file), so the list stays
correct without anyone maintaining it.

Runs automatically at the end of `build_carousel.py --write`; can also be
run directly:  python build_library.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from build_carousel import SLIDES

REPO = Path(__file__).resolve().parent
MARK_BEGIN = "<!-- BEGIN library (managed by build_library.py) -->"
MARK_END = "<!-- END library -->"
SHOW = 12  # rows on the homepage

# Profile pages that live outside articles/ (not carousel slides).
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


def added_date(rel_href: str) -> str:
    """First-commit date (YYYY.MM.DD) of site/<href>; today if uncommitted."""
    out = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ad", "--date=format:%Y.%m.%d",
         "--", f"site/{rel_href}"],
        capture_output=True, text=True, cwd=REPO).stdout.strip().splitlines()
    if out:
        return out[-1]
    from datetime import date
    return date.today().strftime("%Y.%m.%d")


def thumb(img: str) -> str:
    webp = REPO / "site" / "images" / "pinterest" / f"{img}.webp"
    png = REPO / "site" / "images" / "pinterest" / f"{img}.png"
    if webp.exists():
        return f"images/pinterest/{img}.webp"
    if png.exists():
        return f"images/pinterest/{img}.png"
    return ""


def build_rows() -> list[dict]:
    seen, rows = set(), []
    for e in list(SLIDES) + PROFILES:
        if e["href"] in seen:
            continue
        seen.add(e["href"])
        rows.append({**e, "date": added_date(e["href"]), "thumb": thumb(e["img"])})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def render(rows: list[dict]) -> str:
    items = []
    for r in rows[:SHOW]:
        img = (f'<img class="gy-lib-thumb" src="{r["thumb"]}" alt="" '
               f'loading="lazy" decoding="async" />') if r["thumb"] else ""
        items.append(
            f'<a class="gy-lib-row" href="{r["href"]}">'
            f'<span class="gy-lib-date">{r["date"]}</span>'
            f'<span class="gy-lib-body"><span class="gy-lib-tag">{r["tag"]}</span>'
            f'<span class="gy-lib-title">{r["title"]}</span></span>'
            f'{img}</a>')
    body = "\n".join(items)
    return (f"{MARK_BEGIN}\n"
            '<section class="gy-library" id="profiles" data-reveal>\n'
            "  <h2>Latest guides &amp; essays</h2>\n"
            '  <p class="intro">Everything we publish, newest first — '
            "the carousel below draws from the same pool.</p>\n"
            f'  <div class="gy-lib-list">\n{body}\n  </div>\n'
            "</section>\n"
            f"{MARK_END}")


def main() -> None:
    html = render(build_rows())
    for base in ("site", "docs"):
        p = REPO / base / "index.html"
        t = p.read_text(encoding="utf-8")
        if MARK_BEGIN not in t:
            print(f"  !! markers missing in {base}/index.html — run the one-time insert first")
            continue
        start = t.index(MARK_BEGIN)
        end = t.index(MARK_END) + len(MARK_END)
        p.write_text(t[:start] + html + t[end:], encoding="utf-8")
    print(f"  library refreshed ({min(SHOW, len(build_rows()))} rows shown)")


if __name__ == "__main__":
    main()
