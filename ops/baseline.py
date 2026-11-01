#!/usr/bin/env python3
"""Baseline snapshot before a one-element experiment (30-day plan, 2026-11).

Records, for the given pages: GA4 page_view + affiliate_click by placement and device
(last N days) and GSC clicks/impressions/CTR/position (last N days, ending 3 days ago).
Writes ops/state/experiments/baseline-<date>-<label>.json and prints a summary.

  .venv/bin/python ops/baseline.py --label e1 articles/where-to-stay-in-hong-kong.html ...
"""
import argparse, json, os, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); os.chdir(REPO)
import requests  # noqa: E402
import ga4_analyze as G  # noqa: E402
import gsc_analyze as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--label", required=True)
ap.add_argument("--days", type=int, default=28)
ap.add_argument("pages", nargs="+", help="paths like articles/x.html")
a = ap.parse_args()

G._load_env(); S._load_env()
pid = os.getenv("GA4_PROPERTY_ID")
sa = REPO / (os.getenv("GSC_SA_JSON") or "gsc_service_account.json")
gtok, stok = G._session_token(sa), S._session_token(sa)
site = os.getenv("GSC_SITE_URL", "https://gentlyyonder.com/")
today = date.today()
start, end = (today - timedelta(days=a.days)).isoformat(), today.isoformat()
paths = ["/" + p.lstrip("/") for p in a.pages]


def event_rows(name, dims):
    body = {"dateRanges": [{"startDate": start, "endDate": end}], "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": "eventCount"}], "limit": 10000,
            "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": name}}}}
    r = requests.post(G.API.format(pid=pid), headers={"Authorization": f"Bearer {gtok}"}, json=body, timeout=60)
    r.raise_for_status()
    return [([d["value"] for d in x["dimensionValues"]], float(x["metricValues"][0]["value"]))
            for x in r.json().get("rows", [])]


out = {"label": a.label, "taken": end, "ga4_range": [start, end], "pages": {}}
views = defaultdict(float)
for d, n in event_rows("page_view", ["pagePath", "deviceCategory"]):
    if d[0] in paths:
        views[(d[0], d[1])] += n
clicks = defaultdict(lambda: defaultdict(float))
for d, n in event_rows("affiliate_click", ["pagePath", "customEvent:placement", "deviceCategory"]):
    if d[0] in paths:
        clicks[d[0]][f"{d[1]}|{d[2]}"] += n

gend = (today - timedelta(days=3)).isoformat()
gstart = (today - timedelta(days=3 + a.days)).isoformat()
for p in paths:
    url = site.rstrip("/") + p
    rows = S.gsc_query(stok, site, gstart, gend, ["page"],
                       filters=[{"dimension": "page", "operator": "equals", "expression": url}])
    g = rows[0] if rows else {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    q = S.gsc_query(stok, site, gstart, gend, ["query"], row_limit=10,
                    filters=[{"dimension": "page", "operator": "equals", "expression": url}])
    out["pages"][p] = {
        "page_view": {dev: n for (pp, dev), n in views.items() if pp == p},
        "affiliate_click": dict(clicks[p]),
        "gsc": {"range": [gstart, gend], "clicks": g["clicks"], "impressions": g["impressions"],
                "ctr": round(g["ctr"], 5), "position": round(g["position"], 1),
                "top_queries": [(r["keys"][0], r["impressions"], round(r["position"], 1)) for r in
                                sorted(q, key=lambda r: -r["impressions"])[:5]]},
    }
dest = REPO / "ops/state/experiments" / f"baseline-{end}-{a.label}.json"
dest.write_text(json.dumps(out, indent=1, ensure_ascii=False))
for p, v in out["pages"].items():
    g = v["gsc"]
    print(f"{p}\n  views {v['page_view']}\n  clicks {v['affiliate_click']}\n"
          f"  GSC imp {g['impressions']} clicks {g['clicks']} ctr {g['ctr']:.2%} pos {g['position']}")
print("->", dest.relative_to(REPO))
