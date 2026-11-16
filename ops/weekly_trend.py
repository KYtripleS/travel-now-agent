"""Weekly trend check, read-only: is the site growing, and what moved last week?

  1. Real readers per week (Mon-Sun) by channel since June, with engaged sessions and the
     noise that was dropped (same filters as ops/daily.py), and the AI sources per week.
  2. Search Console clicks, impressions and average position per week.
  3. Pages whose Google clicks moved most: last full week against the week two before
     (one week back is skipped so a slow slide is not hidden by a one-day bump).
  4. Affiliate clicks per week by placement, and real sessions / engaged rate by device.

The report is printed and written to ga4_reports/weekly-trend-<date>.md (gitignored).
usage: .venv/bin/python ops/weekly_trend.py
"""
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
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
site = os.getenv("GSC_SITE_URL", "https://gentlyyonder.com/")
today = date.today()
last_mon = today - timedelta(days=today.weekday() + 7)          # start of the last full week
weeks = [(last_mon - timedelta(days=7 * i)) for i in range(3)]  # last, one before, two before
span = lambda m: (m.isoformat(), (m + timedelta(days=6)).isoformat())
wk = lambda d: (d - timedelta(days=d.weekday())).isoformat()
out = []
p = lambda *a: out.append(" ".join(str(x) for x in a))


def event_rows(name, dims, start, end):
    body = {"dateRanges": [{"startDate": start, "endDate": end}], "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": "eventCount"}], "limit": 10000,
            "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": name}}}}
    r = requests.post(G.API.format(pid=pid), headers={"Authorization": f"Bearer {gtok}"}, json=body, timeout=60)
    r.raise_for_status()
    return [([d["value"] for d in x["dimensionValues"]], float(x["metricValues"][0]["value"])) for x in r.json().get("rows", [])]


# 1. readers per week
rows = G.run_report(gtok, pid, dimensions=["date", "sessionDefaultChannelGroup", "sessionSource", "landingPage"],
                    metrics=["sessions", "engagedSessions"], start="2026-06-01", end=span(last_mon)[1], limit=100000)
W = defaultdict(lambda: defaultdict(float)); noise = defaultdict(float); eng = defaultdict(float)
ai = defaultdict(lambda: defaultdict(float))
for r in rows:
    d, ch, s, lp = r["dims"]; w = wk(datetime.strptime(d, "%Y%m%d").date()); n = G._num(r["mets"][0])
    if s in G.NOISE_SOURCES or lp.startswith(G.LEGACY_PREFIX):
        noise[w] += n; continue
    c = {"AI Assistant": "AI", "Organic Search": "Search"}.get(ch, "Social" if "Social" in ch else "Other")
    W[w][c] += n; eng[w] += G._num(r["mets"][1])
    if c == "AI":
        ai[w][s] += n
p(f"# Weekly trend, {today}\n\n## Real readers per week\n")
p("| week | Search | AI | Social | Other | real | engaged | noise | AI sources |\n|---|---|---|---|---|---|---|---|---|")
for w in sorted(W)[-12:]:
    v = W[w]; top = ", ".join(f"{k} {n:.0f}" for k, n in sorted(ai[w].items(), key=lambda x: -x[1])[:3])
    p(f"| {w} | {v['Search']:.0f} | {v['AI']:.0f} | {v['Social']:.0f} | {v['Other']:.0f} | {sum(v.values()):.0f} "
      f"| {eng[w]:.0f} | {noise[w]:.0f} | {top} |")

# 2. Search Console per week
GW = defaultdict(lambda: [0, 0, 0.0])
for r in S.gsc_query(stok, site, "2026-06-01", span(last_mon)[1], ["date"]):
    w = wk(date.fromisoformat(r["keys"][0])); GW[w][0] += r["clicks"]; GW[w][1] += r["impressions"]
    GW[w][2] += r["position"] * r["impressions"]
p("\n## Search Console per week\n\n| week | clicks | impressions | avg position |\n|---|---|---|---|")
for w in sorted(GW)[-12:]:
    c, i, pos = GW[w]; p(f"| {w} | {c} | {i} | {pos / max(i, 1):.1f} |")


# 3. page movers
def pages(m):
    a, b = span(m)
    return {r["keys"][0].replace("https://gentlyyonder.com", ""): (r["clicks"], r["impressions"], r["position"])
            for r in S.gsc_query(stok, site, a, b, ["page"])}


A, B = pages(weeks[2]), pages(weeks[0])
moved = sorted(set(A) | set(B), key=lambda k: B.get(k, (0,))[0] - A.get(k, (0,))[0])
p(f"\n## Google clicks by page, week {weeks[2]} -> week {weeks[0]}\n")
p("| page | clicks | impressions | position |\n|---|---|---|---|")
for k in moved[:8] + moved[-8:]:
    a, b = A.get(k, (0, 0, 0)), B.get(k, (0, 0, 0))
    if a[0] == b[0]:
        continue
    p(f"| {k} | {a[0]:.0f} -> {b[0]:.0f} | {a[1]:.0f} -> {b[1]:.0f} | {a[2]:.1f} -> {b[2]:.1f} |")

# 4. affiliate clicks by placement, engagement by device
p("\n## Affiliate clicks and engagement per week\n")
for m in reversed(weeks):
    a, b = span(m)
    ev = event_rows("affiliate_click", ["customEvent:placement"], a, b)
    rows = G.run_report(gtok, pid, dimensions=["sessionSource", "landingPage", "deviceCategory"],
                        metrics=["sessions", "engagedSessions"], start=a, end=b, limit=20000)
    dev = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        s, lp, dv = r["dims"]
        if s in G.NOISE_SOURCES or lp.startswith(G.LEGACY_PREFIX):
            continue
        dev[dv][0] += G._num(r["mets"][0]); dev[dv][1] += G._num(r["mets"][1])
    pl = ", ".join(f"{k[0]} {n:.0f}" for k, n in sorted(ev, key=lambda x: -x[1]))
    dv = ", ".join(f"{k} {v[0]:.0f} ({v[1] / v[0]:.0%} engaged)" for k, v in sorted(dev.items(), key=lambda x: -x[1][0]))
    p(f"- **{a}**: {sum(n for _, n in ev):.0f} clicks ({pl}); {dv}")

text = "\n".join(out)
print(text)
dest = REPO / "ga4_reports" / f"weekly-trend-{today}.md"
dest.parent.mkdir(exist_ok=True); dest.write_text(text + "\n")
print(f"\nwrote {dest.relative_to(REPO)}")
