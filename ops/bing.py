"""Bing Webmaster check, read-only. Prints a short report and writes ga4_reports/bing-<date>.json (gitignored):

  - inbound links Bing knows about: which of our pages are linked, and from which domains
  - Bing clicks and impressions by week, last 8 weeks
  - top Bing queries by impressions

Needs BING_WEBMASTER_API_KEY in .env (Bing Webmaster Tools > Settings > API access).

usage: .venv/bin/python ops/bing.py
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); os.chdir(REPO)
import requests  # noqa: E402
import gsc_analyze as S  # noqa: E402

S._load_env()
KEY = os.getenv("BING_WEBMASTER_API_KEY", "").strip()
SITE = "https://gentlyyonder.com/"
API = "https://ssl.bing.com/webmaster/api.svc/json/"
if not KEY:
    sys.exit("BING_WEBMASTER_API_KEY is empty in .env")


def call(method, **params):
    r = requests.get(API + method, params={"siteUrl": SITE, "apikey": KEY, **params}, timeout=60)
    if r.status_code != 200:
        sys.exit(f"{method}: HTTP {r.status_code} {r.text[:200]}")
    return r.json()["d"]


def when(s):  # "/Date(1792540800000)/" or "/Date(1792540800000-0700)/"
    return datetime.fromtimestamp(int(re.search(r"-?\d{10,}", s).group()) / 1000, timezone.utc).date()


# inbound links: pages of ours with links, then who links to each
linked, page = [], 0
while True:
    d = call("GetLinkCounts", page=page)
    linked += [(x["Url"], x["Count"]) for x in d.get("Links") or []]
    page += 1
    if page >= d.get("TotalPages", 0):
        break
sources = defaultdict(list)
for url, _ in linked:
    page = 0
    while True:
        d = call("GetUrlLinks", link=url, page=page)
        for x in d.get("Details") or []:
            sources[urlparse(x["Url"]).netloc.lower().removeprefix("www.")].append(
                {"from": x["Url"], "to": url, "anchor": x.get("AnchorText", "")})
        page += 1
        if page >= d.get("TotalPages", 0):
            break

traffic = call("GetRankAndTrafficStats")
weeks = defaultdict(lambda: [0, 0])
cutoff = date.today() - timedelta(weeks=8)
for x in traffic:
    day = when(x["Date"])
    if day >= cutoff:
        wk = day - timedelta(days=day.weekday())
        weeks[wk][0] += x["Clicks"]; weeks[wk][1] += x["Impressions"]
queries = sorted(call("GetQueryStats"), key=lambda x: -x["Impressions"])[:15]

print(f"inbound links: {sum(c for _, c in linked)} to {len(linked)} pages, from {len(sources)} domains")
for dom, links in sorted(sources.items(), key=lambda kv: -len(kv[1]))[:20]:
    print(f"   {dom}: {len(links)}  e.g. {links[0]['to'].replace(SITE, '/')}")
print("top linked pages:", [(u.replace(SITE, "/"), c) for u, c in sorted(linked, key=lambda x: -x[1])[:8]])
print("Bing weekly [clicks, impressions]:", [(w.isoformat(), v) for w, v in sorted(weeks.items())])
print("top Bing queries:", [(q["Query"], q["Impressions"], q["Clicks"], round(q.get("AvgImpressionPosition", 0), 1)) for q in queries])

out = REPO / "ga4_reports" / f"bing-{date.today().isoformat()}.json"
out.write_text(json.dumps({
    "linked_pages": linked, "sources": sources, "anchors": Counter(l["anchor"] for v in sources.values() for l in v).most_common(30),
    "weekly": {w.isoformat(): v for w, v in weeks.items()}, "queries": queries,
}, indent=1, default=str))
print("wrote", out.relative_to(REPO))
