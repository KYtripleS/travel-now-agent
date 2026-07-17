#!/usr/bin/env python3
"""
rank_popular.py — rank site pages by real reader traffic (28 days).

Blends GSC (clicks, impressions) + GA4 (sessions by landing page) into
data/popular_pages.csv, which build_library.py uses to render the homepage
"Most read" strip. Refresh: python3 rank_popular.py && python3 build_library.py

Score = 6*GSC clicks + 3*GA4 sessions + 0.02*GSC impressions
(behaviour first, demand as tiebreak).
"""
from __future__ import annotations

import csv
import os
from datetime import date, timedelta
from pathlib import Path

import gsc_analyze as G
import ga4_analyze as A

REPO = Path(__file__).resolve().parent
OUT = REPO / "data" / "popular_pages.csv"
DAYS = 28
EXCLUDE = {"", "index.html", "about.html", "privacy.html", "editors.html",
           "methodology.html", "editorial.html", "contribute.html",
           "all-guides.html", "404.html"}


def norm(path: str) -> str:
    """'/countries/japan/' -> 'countries/japan/index.html' (repo-relative href)."""
    p = path.split("?")[0].split("#")[0]
    p = p.lstrip("/")
    # legacy GitHub Pages prefix (kytriples.github.io/travel-now-agent/...)
    if p == "travel-now-agent" or p.startswith("travel-now-agent/"):
        p = p[len("travel-now-agent"):].lstrip("/")
    if p.endswith("/") or p == "":
        p += "index.html"
    return p


def main() -> None:
    G._load_env()
    site = os.getenv("GSC_SITE_URL", "https://gentlyyonder.com/")
    end = (date.today() - timedelta(days=1)).isoformat()
    start = (date.today() - timedelta(days=DAYS)).isoformat()

    g_tok = G._session_token(REPO / os.getenv("GSC_SA_JSON", "gsc_service_account.json"))
    gsc = {}
    for d in G.rows_to_dicts(G.gsc_query(g_tok, site, start, end, ["page"]), ["page"]):
        p = norm(d["page"].replace(site, "/"))
        cur = gsc.setdefault(p, {"clicks": 0, "impr": 0})
        cur["clicks"] += d["clicks"]
        cur["impr"] += d["impressions"]

    pid = os.getenv("GA4_PROPERTY_ID", "541637640")
    a_tok = A._session_token(REPO / os.getenv("GSC_SA_JSON", "gsc_service_account.json"))
    ga = {}
    for row in A.run_report(a_tok, pid, dimensions=["landingPage"], metrics=["sessions"],
                            start=start, end=end, limit=250, order_by_metric="sessions"):
        p = norm(row["dims"][0])
        if p == "(not set)":
            continue
        ga[p] = ga.get(p, 0) + int(float(row["mets"][0]))

    pages = {}
    for p in set(gsc) | set(ga):
        if p in EXCLUDE:
            continue
        c = gsc.get(p, {}).get("clicks", 0)
        i = gsc.get(p, {}).get("impr", 0)
        s = ga.get(p, 0)
        pages[p] = {"score": round(6 * c + 3 * s + 0.02 * i, 2),
                    "clicks": c, "sessions": s, "impressions": i}

    ranked = sorted(pages.items(), key=lambda kv: -kv[1]["score"])
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "score", "clicks", "sessions", "impressions",
                    f"# {start}..{end} score=6c+3s+0.02i"])
        for p, v in ranked:
            if v["score"] <= 0:
                continue
            w.writerow([p, v["score"], v["clicks"], v["sessions"], v["impressions"], ""])
    print(f"Wrote {OUT.relative_to(REPO)} — {len(ranked)} pages, top 10:")
    for p, v in ranked[:10]:
        print(f'  {v["score"]:>7}  c{v["clicks"]} s{v["sessions"]} i{v["impressions"]}  {p}')


if __name__ == "__main__":
    main()
