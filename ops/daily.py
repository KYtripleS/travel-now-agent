"""Daily check, read-only. Prints a short report and writes ga4_reports/daily-<date>.json (gitignored):

  - real readers by day and channel, last 14 days (known noise sources dropped)
  - affiliate clicks last 7 days by page and partner, and the prior 7 days' total
  - top AI-assistant landing pages and top sources, last 7 days
  - Search Console clicks and impressions, last 7 days against the 7 before
  - real sessions from the US, UK, Canada, Australia and New Zealand, last 30 days: Journey by
    Mediavine takes sites from 1,000 such sessions a month (Mediavine, 2026)

usage: .venv/bin/python ops/daily.py
"""
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); os.chdir(REPO)
import requests  # noqa: E402
import ga4_analyze as G  # noqa: E402
import gsc_analyze as S  # noqa: E402

G._load_env(); S._load_env()
pid = os.getenv("GA4_PROPERTY_ID")
sa = REPO / (os.getenv("GSC_SA_JSON") or "gsc_service_account.json")
gtok, stok = G._session_token(sa), S._session_token(sa)
today = date.today()
iso = lambda d: d.isoformat()
real = lambda src, lp: not (src in G.NOISE_SOURCES or lp.startswith(G.LEGACY_PREFIX))
chan = lambda ch: {"AI Assistant": "AI", "Organic Search": "Search"}.get(ch, "Social" if "Social" in ch else "Other")


def event_rows(name, dims, start, end):
    body = {"dateRanges": [{"startDate": start, "endDate": end}], "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": "eventCount"}], "limit": 10000,
            "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": name}}}}
    r = requests.post(G.API.format(pid=pid), headers={"Authorization": f"Bearer {gtok}"}, json=body, timeout=60)
    r.raise_for_status()
    return [([d["value"] for d in x["dimensionValues"]], float(x["metricValues"][0]["value"])) for x in r.json().get("rows", [])]


out = {}
rows = G.run_report(gtok, pid, dimensions=["date", "sessionDefaultChannelGroup", "sessionSource", "landingPage"],
                    metrics=["sessions"], start=iso(today - timedelta(days=14)), end=iso(today), limit=20000)
day = defaultdict(lambda: defaultdict(float)); ai_lp = defaultdict(float); src = defaultdict(float)
cut = (today - timedelta(days=7)).strftime("%Y%m%d")
for r in rows:
    d, ch, s, lp = r["dims"]
    if not real(s, lp):
        continue
    n = G._num(r["mets"][0]); day[d][chan(ch)] += n
    if d > cut:
        src[s] += n
        if chan(ch) == "AI":
            ai_lp[lp] += n
out["by_day"] = {d: dict(v) for d, v in sorted(day.items())}
top = lambda m, k=10: sorted(m.items(), key=lambda x: -x[1])[:k]
out["src7"], out["ai_lp7"] = top(src), top(ai_lp)
a7 = event_rows("affiliate_click", ["pagePath", "customEvent:partner"], iso(today - timedelta(days=7)), iso(today))
p7 = event_rows("affiliate_click", ["eventName"], iso(today - timedelta(days=14)), iso(today - timedelta(days=8)))
out["aff7"] = sorted([d + [n] for d, n in a7], key=lambda x: -x[-1])
out["aff7_total"], out["aff_prev7_total"] = sum(n for _, n in a7), sum(n for _, n in p7)

PREMIUM = {"United States", "United Kingdom", "Canada", "Australia", "New Zealand"}
geo = G.run_report(gtok, pid, dimensions=["country", "sessionSource", "landingPage"], metrics=["sessions"],
                   start=iso(today - timedelta(days=30)), end=iso(today), limit=20000)
real30 = [(r["dims"][0], G._num(r["mets"][0])) for r in geo if real(r["dims"][1], r["dims"][2])]
out["sessions30"] = int(sum(n for _, n in real30))
out["premium30"] = int(sum(n for c, n in real30 if c in PREMIUM))

site = "https%3A%2F%2Fgentlyyonder.com%2F"
end = today - timedelta(days=3)


def gsc(start, stop, dims, limit=25):
    body = {"startDate": iso(start), "endDate": iso(stop), "dimensions": dims, "rowLimit": limit}
    r = requests.post(f"https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query",
                      headers={"Authorization": f"Bearer {stok}"}, json=body, timeout=60)
    r.raise_for_status()
    return r.json().get("rows", [])


cur = gsc(end - timedelta(days=6), end, ["date"], 10); prev = gsc(end - timedelta(days=13), end - timedelta(days=7), ["date"], 10)
tot = lambda rs: [sum(x["clicks"] for x in rs), sum(x["impressions"] for x in rs)]
out["gsc_window"] = [iso(end - timedelta(days=6)), iso(end)]
out["gsc_tot"] = {"cur": tot(cur), "prev": tot(prev)}
out["gsc_top"] = [[x["keys"][0].replace("https://gentlyyonder.com/", ""), x["clicks"], x["impressions"], round(x["position"], 1)]
                  for x in sorted(gsc(end - timedelta(days=6), end, ["page"], 50), key=lambda x: -x["impressions"])[:12]]

path = REPO / "ga4_reports" / f"daily-{iso(today)}.json"
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(out, indent=1, ensure_ascii=False))
for d, v in list(out["by_day"].items())[-7:]:
    print(d, {k: int(x) for k, x in v.items()}, int(sum(v.values())))
print("affiliate clicks 7d:", int(out["aff7_total"]), "prev 7d:", int(out["aff_prev7_total"]))
for r in out["aff7"][:10]:
    print("  ", r)
print("sources 7d:", out["src7"][:6])
print("AI landing 7d:", out["ai_lp7"][:6])
print("GSC", out["gsc_window"], out["gsc_tot"])
print(f"30d real sessions {out['sessions30']}, from US/UK/CA/AU/NZ {out['premium30']} (Journey needs 1,000)")
print(f"wrote {path.relative_to(REPO)}")
