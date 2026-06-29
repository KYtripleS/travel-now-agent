#!/usr/bin/env python3
"""
discover_keywords.py  —  Agent #2: keyword & opportunity finder

Two modes, both write a ranked action report to
marketing/keyword-opportunities.md:

1. GSC mode (--gsc <csv>): point it at a Search Console "Queries" export
   (Performance -> Queries -> Export -> CSV/Sheets). It classifies every
   query into the action that will move the needle fastest:
     * STRIKING DISTANCE — position 5-20 with real impressions: the page
       exists and is close to page 1; improve on-page + internal links.
     * CTR FIX — already top ~10 but few/no clicks: rewrite title + meta.
     * NEW ARTICLE — impressions on a query we don't have a page for yet.

2. Idea mode (always runs): generates long-tail article ideas by crossing
   our covered topics with high-intent modifiers (destinations, trip
   lengths, traveler types), skipping anything we already publish. This
   gives a content backlog even before there's GSC data.

Usage:
  python discover_keywords.py                       # idea mode only
  python discover_keywords.py --gsc ~/Downloads/Queries.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
OUT = REPO / "marketing" / "keyword-opportunities.md"

MODIFIERS = {
    "destination": ["Japan", "South Korea", "Vietnam", "Thailand", "Europe",
                    "Bali", "the USA", "Australia"],
    "trip_length": ["a weekend", "a 10-day trip", "a 2-week trip", "a month abroad"],
    "traveler": ["digital nomads", "first-time travelers", "families", "carry-on only",
                 "solo female travelers", "budget travelers"],
}

# Covered topic -> which modifier axis produces useful long-tail variants
TOPIC_SEEDS = {
    "carry-on packing list": "trip_length",
    "eSIM": "destination",
    "travel insurance": "traveler",
    "what to pack": "destination",
    "airport security": "traveler",
    "capsule wardrobe": "trip_length",
    "pocket wifi": "destination",
    "things to do": "destination",
}


def covered_slugs() -> set[str]:
    slugs = {p.stem for p in (SITE / "articles").glob("*.html")}
    slugs |= {p.parent.name for p in SITE.glob("countries/*/index.html")}
    slugs |= {p.parent.name for p in SITE.glob("cities/*/index.html")}
    return slugs


def covered_text() -> str:
    """Lowercased blob of all article titles/slugs for fuzzy 'do we cover it' checks."""
    blob = " ".join(p.stem.replace("-", " ") for p in (SITE / "articles").glob("*.html"))
    return blob.lower()


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------- GSC mode ----------

def parse_gsc(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # tolerate header variants
            q = r.get("Query") or r.get("query") or r.get("Top queries")
            if not q:
                continue
            def num(*keys):
                for k in keys:
                    v = r.get(k)
                    if v not in (None, ""):
                        return re.sub(r"[%,]", "", v).strip()
                return "0"
            try:
                rows.append({
                    "query": q.strip(),
                    "clicks": float(num("Clicks", "clicks")),
                    "impressions": float(num("Impressions", "impressions")),
                    "ctr": float(num("CTR", "ctr") or 0),
                    "position": float(num("Position", "position") or 0),
                })
            except ValueError:
                continue
    return rows


def classify(rows: list[dict], blob: str) -> dict[str, list[dict]]:
    buckets = {"striking": [], "ctr_fix": [], "new": []}
    for r in rows:
        pos, imp, clk = r["position"], r["impressions"], r["clicks"]
        # crude "do we cover it": any significant word from the query in our titles
        words = [w for w in re.findall(r"[a-z]+", r["query"].lower()) if len(w) > 3]
        covered = sum(1 for w in words if w in blob) >= max(1, len(words) // 2)
        if not covered and imp >= 2:
            buckets["new"].append(r)
        elif 5 <= pos <= 20 and imp >= 3:
            buckets["striking"].append(r)
        elif pos <= 10 and clk == 0 and imp >= 3:
            buckets["ctr_fix"].append(r)
    for k in buckets:
        buckets[k].sort(key=lambda r: r["impressions"], reverse=True)
    return buckets


def gsc_section(buckets: dict) -> str:
    L = ["## Search Console opportunities (ranked by impressions)\n"]
    def tbl(rows, cols):
        out = ["| Query | Impr | Pos | Clicks |", "|---|---|---|---|"]
        for r in rows[:15]:
            out.append(f"| {r['query']} | {r['impressions']:.0f} | {r['position']:.1f} | {r['clicks']:.0f} |")
        return "\n".join(out)

    L.append("### 🎯 Striking distance (pos 5–20) — optimize the existing page")
    L.append("_Add internal links, tighten the on-page answer, expand the section that matches the query._\n")
    L.append(tbl(buckets["striking"], None) if buckets["striking"] else "_none yet_")
    L.append("\n### ✏️ CTR fix (top ~10, no clicks) — rewrite title + meta")
    L.append("_The rank is fine; the headline isn't earning the click. Add a year, a number, or a benefit._\n")
    L.append(tbl(buckets["ctr_fix"], None) if buckets["ctr_fix"] else "_none yet_")
    L.append("\n### 🆕 New article (impressions, no matching page)")
    L.append("_Google is showing us for these but we have no dedicated page. Write one._\n")
    L.append(tbl(buckets["new"], None) if buckets["new"] else "_none yet_")
    return "\n".join(L) + "\n"


# ---------- Idea mode ----------

def idea_section(blob: str) -> str:
    L = ["## Long-tail article ideas (from current coverage)\n",
         "_Crossed our topics with high-intent modifiers; skipped anything we seem to cover._\n"]
    seen = set()
    for topic, axis in TOPIC_SEEDS.items():
        for mod in MODIFIERS[axis]:
            idea = f"{topic} for {mod}"
            slug = slugify(idea)
            key = slug
            if key in seen:
                continue
            seen.add(key)
            # skip if clearly covered
            base = topic.split()[0]
            L.append(f"- **{idea}** — `articles/{slug}.html`")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gsc", help="path to a Search Console Queries CSV export")
    args = ap.parse_args()

    blob = covered_text()
    parts = ["# Keyword & opportunity report",
             "",
             "Generated by `discover_keywords.py`. Work top-down: striking-distance "
             "and CTR fixes pay off fastest because the page already ranks.",
             ""]

    if args.gsc:
        path = Path(args.gsc).expanduser()
        if not path.exists():
            print(f"  ⚠ GSC file not found: {path}")
        else:
            rows = parse_gsc(path)
            buckets = classify(rows, blob)
            parts.append(gsc_section(buckets))
            print(f"  parsed {len(rows)} queries — "
                  f"{len(buckets['striking'])} striking, {len(buckets['ctr_fix'])} CTR-fix, "
                  f"{len(buckets['new'])} new-article")
    else:
        parts.append("> No GSC export passed (`--gsc <csv>`). Showing idea mode only.\n")
        print("  idea mode (no --gsc CSV given)")

    parts.append(idea_section(blob))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"  wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
