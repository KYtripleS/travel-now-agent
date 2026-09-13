#!/usr/bin/env python3
"""
build_search_index.py — generate the client-side search index.

GitHub Pages is static, so site search has to run in the browser. This walks
site/*.html, pulls a title / summary / category / destination tags out of each
page, and writes a compact JSON index that site/js/gy-search.js loads once.

Only 39 of ~190 pages carry a meta description, so the summary falls back to
the first real body paragraph (nav, CTA asides and the footer are stripped
first, or every page would summarise as "Gently Yonder is an independent...").

Keys are short (u/t/d/c/k) purely to keep the payload small.

  python build_search_index.py          # writes site/ + docs/
"""

from __future__ import annotations

import html as htmllib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
DOCS = REPO / "docs"
OUT_REL = Path("data/search-index.json")

# Pages that must never appear in results.
SKIP_NAMES = {
    "googlee46af4b13b14f75e.html",
    "search.html",
    "ready-score-pro-thanks.html",
    "privacy.html",
    "404.html",
}
SKIP_DIRS = {"go"}  # /go/* are noindex short-redirects

STRIP_BLOCKS = re.compile(
    r"<(script|style|nav|footer|aside|figure|form)\b[^>]*>.*?</\1>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")

# Destination aliases -> extra searchable keywords, so "oz" or "nihon" still
# find the right pages and multi-word places match a one-word query.
ALIASES = {
    "tokyo": "japan japanese honshu",
    "kyoto": "japan japanese kansai",
    "osaka": "japan japanese kansai",
    "okinawa": "japan japanese naha",
    "japan": "japanese nippon nihon",
    "seoul": "korea korean south-korea",
    "korea": "korean seoul busan",
    "bangkok": "thailand thai",
    "thailand": "thai bangkok phuket",
    "singapore": "sg singaporean",
    "sydney": "australia australian nsw",
    "melbourne": "australia australian victoria",
    "perth": "australia australian",
    "australia": "australian aussie sydney melbourne",
    "taipei": "taiwan taiwanese",
    "taiwan": "taiwanese taipei",
    "hanoi": "vietnam vietnamese",
    "vietnam": "vietnamese hanoi saigon",
    "saigon": "vietnam ho-chi-minh vietnamese",
    "bali": "indonesia indonesian denpasar ubud",
    "manila": "philippines filipino",
    "cebu": "philippines filipino",
    "penang": "malaysia malaysian george-town",
    "kuala": "malaysia malaysian kl",
    "hong": "hong-kong hongkong china",
    "esim": "sim data roaming connectivity mobile",
    "insurance": "medical cover policy",
    "packing": "luggage suitcase bag carry-on",
}


def clean(text: str) -> str:
    """Strip tags, collapse whitespace, and decode entities (&amp; -> &) so
    titles render as written instead of leaking markup into results."""
    return WS.sub(" ", htmllib.unescape(TAG.sub(" ", text))).strip()


def summary_of(html: str) -> str:
    """Meta description if present, else the first real body paragraph."""
    m = re.search(r'<meta name="description" content="([^"]+)"', html, re.I)
    if m:
        return clean(m.group(1))[:200]
    body = STRIP_BLOCKS.sub(" ", html)
    start = body.find("</h1>")
    if start != -1:
        body = body[start:]
    for para in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S | re.I):
        txt = clean(para)
        if len(txt) >= 60 and "affiliate" not in txt.lower()[:40]:
            return txt[:200]
    return ""


def title_of(html: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m and clean(m.group(1)):
        return clean(m.group(1))
    m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    t = clean(m.group(1)) if m else ""
    return re.sub(r"\s*[|]\s*Gently Yonder\s*$", "", t)


def category_of(html: str, rel: str) -> str:
    m = re.search(r'"articleSection"\s*:\s*"([^"]+)"', html)
    if m:
        return m.group(1)
    head = rel.split("/")[0]
    return {
        "articles": "Guide",
        "cities": "City Guide",
        "countries": "Country Profile",
        "tools": "Tool",
        "travel-power": "Reference",
    }.get(head, "Page")


def keywords_for(rel: str, title: str) -> str:
    """Slug + title words, plus aliases, so 'sydney' reaches Australia pages."""
    words = set(re.split(r"[^a-z0-9]+", (rel + " " + title).lower()))
    words.discard("")
    extra: set[str] = set()
    for w in words:
        if w in ALIASES:
            extra.update(ALIASES[w].split())
    return " ".join(sorted(words | extra))


def main() -> None:
    entries = []
    for path in sorted(SITE.rglob("*.html")):
        rel = path.relative_to(SITE).as_posix()
        if path.name in SKIP_NAMES or path.name.startswith("_"):
            continue
        if rel.split("/")[0] in SKIP_DIRS:
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        if 'name="robots" content="noindex' in html:
            continue
        title = title_of(html)
        if not title:
            continue
        entries.append({
            "u": rel,
            "t": title,
            "d": summary_of(html),
            "c": category_of(html, rel),
            "k": keywords_for(rel, title),
        })

    payload = json.dumps(
        {"n": len(entries), "docs": entries}, ensure_ascii=False, separators=(",", ":"))
    for base in (SITE, DOCS):
        out = base / OUT_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload, encoding="utf-8")
    kb = len(payload.encode("utf-8")) / 1024
    print(f"  search index: {len(entries)} pages, {kb:.1f} KB -> site/ + docs/{OUT_REL}")


if __name__ == "__main__":
    main()
