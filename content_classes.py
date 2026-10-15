"""Which pages may carry promotions, and which may not.

Monetisation components (promotions.py, and any later placement rule) ask this
module before touching a page. A page is one of:

  historical  country and city profiles (site/countries/, site/cities/) and any
              article labelled "Country profile": their history sections carry
              no affiliate or promotional material (CLAUDE.md affiliate rules)
  trust       About, Editorial, Privacy, Promise, Corrections and the other
              pages that explain how the site works: never monetised
  redirect    a folded article that only forwards to another page
  review      a label where history or culture is the subject ("Culture"):
              left alone until an editor moves it to eligible or historical
  eligible    everything else

The result is written to data/content_classes.csv so an editor can read the
whole list and override any row in OVERRIDES below.

usage: python content_classes.py          # rewrite data/content_classes.csv
       python content_classes.py --print  # also print the counts
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
OUT = REPO / "data" / "content_classes.csv"

TRUST_PAGES = {"about.html", "editorial.html", "editors.html", "privacy.html", "promise.html",
               "corrections.html", "methodology.html", "contribute.html", "404.html"}
HISTORICAL_LABELS = {"Country profile"}
REVIEW_LABELS = {"Culture"}
# rel path -> (class, reason): an editor's decision beats the rules above
OVERRIDES: dict[str, tuple[str, str]] = {}


def _label(html: str) -> str:
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else data.get("@graph", [data]):
            if isinstance(item, dict) and item.get("articleSection"):
                return str(item["articleSection"])
    return ""


def classify(rel: str, html: str) -> tuple[str, str, str]:
    """(class, label, reason) for a page path relative to site/."""
    label = _label(html)
    if rel in OVERRIDES:
        return OVERRIDES[rel][0], label, OVERRIDES[rel][1]
    if rel.startswith(("countries/", "cities/")):
        return "historical", label, "country or city profile"
    if rel in TRUST_PAGES:
        return "trust", label, "explains the site; never monetised"
    if 'http-equiv="refresh"' in html[:4000]:
        return "redirect", label, "folded into another page"
    if label in HISTORICAL_LABELS:
        return "historical", label, f"labelled {label}"
    if label in REVIEW_LABELS:
        return "review", label, f"labelled {label}: needs an editor's call"
    return "eligible", label, ""


def load() -> dict[str, str]:
    """rel path -> class, from the CSV (rebuilt if missing)."""
    if not OUT.exists():
        build()
    with OUT.open() as f:
        return {r["path"]: r["class"] for r in csv.DictReader(f)}


def is_eligible(rel: str) -> bool:
    return load().get(rel) == "eligible"


def build() -> list[dict]:
    rows = []
    pages = sorted(SITE.glob("articles/*.html")) + sorted(SITE.glob("countries/**/*.html")) \
        + sorted(SITE.glob("cities/**/*.html")) + sorted(SITE / p for p in TRUST_PAGES if (SITE / p).exists())
    for p in pages:
        rel = p.relative_to(SITE).as_posix()
        cls, label, reason = classify(rel, p.read_text(encoding="utf-8"))
        rows.append({"path": rel, "class": cls, "label": label, "reason": reason})
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "class", "label", "reason"])
        w.writeheader()
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    if "--print" in sys.argv:
        from collections import Counter
        for cls, n in Counter(r["class"] for r in rows).most_common():
            print(f"{cls:11} {n}")
        for r in rows:
            if r["class"] in ("historical", "review"):
                print(f"  {r['class']:10} {r['path']}  ({r['reason']})")
    print(f"wrote {OUT.relative_to(REPO)} ({len(rows)} pages)")
