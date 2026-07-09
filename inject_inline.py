#!/usr/bin/env python3
"""
inject_inline.py — weave contextual affiliate links into article prose.

Scoped to the body only (between <main> and the tp-inject CTA / <footer>), so it
never touches <head>, the photo figures' credits, or the bottom CTA block.
Idempotent: skips an anchor already wrapped, and won't reuse the same brand twice
in one article. Wraps the FIRST plain-text occurrence of each anchor phrase.

    python inject_inline.py --dry-run   # preview
    python inject_inline.py             # apply (site + docs)
"""
from __future__ import annotations

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent
REL = 'rel="nofollow sponsored noopener" target="_blank"'
MAX_PER_ARTICLE = 3

TPX = {
    "aviasales": "https://aviasales.tpx.lu/dESAKheX",
    "tiqets": "https://tiqets.tpx.lu/7rZHQkfx",
    "radicalstorage": "https://radicalstorage.tpx.lu/WpAnAq1c",
    "klook": "https://klook.tpx.lu/TgR5Suzs",
    "welcomepickups": "https://tpx.lu/YtuAbaB1",
    "saily": "https://saily.tpx.lu/hk5XU6Sm",
    "ekta": "https://ektatraveling.tpx.lu/LXmPxVUQ",
    "kkday": "https://kkday.tpx.lu/99SKEU6d",
}

# Candidate (anchor phrase, brand). First found per brand wins, capped at 3/article.
RULES: dict[str, list[tuple[str, str]]] = {
    "narita-haneda-to-central-tokyo": [
        ("the Narita Express", "klook"),
        ("Keisei Skyliner", "klook"),
        ("airport limousine bus", "klook"),
        ("a private car", "welcomepickups"),
        ("private pickup", "welcomepickups"),
        ("a taxi", "welcomepickups"),
        ("an eSIM", "saily"),
    ],
    "tokyo-to-kyoto-shinkansen-vs-flight-vs-bus": [
        ("the Japan Rail Pass", "klook"),
        ("a Japan Rail Pass", "klook"),
        ("The flight itself", "aviasales"),
        ("the flight itself", "aviasales"),
    ],
    "osaka-or-kyoto-where-to-base": [
        ("an eSIM", "saily"),
        ("guided experiences", "kkday"),
        ("local experiences", "kkday"),
        ("day trips", "klook"),
        ("day trip", "klook"),
    ],
    "japan-city-sightseeing-passes-worth-it": [
        ("individual tickets", "tiqets"),
        ("single tickets", "tiqets"),
        ("individual entry", "tiqets"),
        ("entry fees", "tiqets"),
        ("guided", "klook"),
        ("a pass", "klook"),
    ],
    "first-day-in-tokyo-arrival-plan": [
        ("an eSIM", "saily"),
        ("getting connected", "saily"),
        ("airport pickup", "welcomepickups"),
        ("a private car", "welcomepickups"),
        ("drop your bags", "radicalstorage"),
        ("dropping bags", "radicalstorage"),
        ("luggage", "radicalstorage"),
    ],
}


def body_bounds(html: str) -> tuple[int, int]:
    start = html.find("<main")
    if start == -1:
        start = html.find("<h1")
    end = html.find("<!-- BEGIN tp-inject")
    if end == -1:
        end = html.find("<footer")
    return start, end


def anchor(url: str, text: str) -> str:
    return f'<a class="gy-inline" href="{url}" {REL}>{text}</a>'


def process(html: str) -> tuple[str, list[str]]:
    start, end = body_bounds(html)
    if start == -1 or end == -1 or start >= end:
        return html, []
    head, region, tail = html[:start], html[start:end], html[end:]
    used_brands: set[str] = set()
    wrapped: list[str] = []
    for phrase, brand in RULES_ACTIVE:
        if len(wrapped) >= MAX_PER_ARTICLE:
            break
        if brand in used_brands:
            continue
        url = TPX[brand]
        if url in region:            # already linked somewhere in body
            used_brands.add(brand)
            continue
        idx = region.find(phrase)
        if idx == -1:
            continue
        # don't wrap if this occurrence sits inside an existing tag/link
        lt, gt = region.rfind("<", 0, idx), region.rfind(">", 0, idx)
        if lt > gt:                  # inside a tag
            continue
        region = region[:idx] + anchor(url, phrase) + region[idx + len(phrase):]
        used_brands.add(brand)
        wrapped.append(f"{brand}:{phrase}")
    return head + region + tail, wrapped


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    global RULES_ACTIVE
    for slug, rules in RULES.items():
        RULES_ACTIVE = rules
        changed = []
        for base in ("site", "docs"):
            p = REPO / base / "articles" / f"{slug}.html"
            if not p.exists():
                continue
            html = p.read_text(encoding="utf-8")
            new, wrapped = process(html)
            if wrapped and not args.dry_run:
                p.write_text(new, encoding="utf-8")
            if base == "site":
                changed = wrapped
        print(f"  {slug:48s} {'(dry) ' if args.dry_run else ''}{changed or 'no anchors found'}")


if __name__ == "__main__":
    main()
