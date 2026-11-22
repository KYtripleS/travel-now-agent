"""How each money page is doing: Google, readers, partner clicks and earnings, on one row (2026-11-22).

For the weekly PDCA (scheduled task gy-weekly-revenue-pdca). Each row is a ticket, tour, car-hire or stay
page, joining four sources over the same window:
  - Search Console: impressions, clicks, average position and the top query (GSC lags about 2 days);
  - GA4: page views and affiliate_click events, by partner;
  - Travelpayouts (ops/tp_sales.py) and Stay22 (ops/stay22_report.py): bookings and commission, matched to
    the page through the sub id or campaign that gy-reveal.js stamps on every partner link.
Amazon, Awin and Impact have no reporting API wired here, so their earnings are not in these numbers.

Read-only. Writes ga4_reports/money-pages-<date>.md (gitignored) and prints the path.
usage: .venv/bin/python ops/money_pages_report.py [--days 28] [--new 28]
       --new N also lists, apart, the pages first published in the last N days (from git).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "ops"))
os.chdir(REPO)
import requests  # noqa: E402
import ga4_analyze as G  # noqa: E402
import gsc_analyze as S  # noqa: E402
import epc as E  # noqa: E402

PREFIXES = ("where-to-buy-", "where-to-book-", "car-rental-", "where-to-stay-")


def money_pages() -> list[str]:
    return sorted(p.stem for p in (REPO / "site" / "articles").glob("*.html") if p.stem.startswith(PREFIXES))


def published_since(days: int) -> dict[str, str]:
    out = subprocess.run(["git", "log", "--diff-filter=A", f"--since={days} days ago", "--format=%ad",
                          "--date=short", "--name-only", "--", "site/articles/"],
                         capture_output=True, text=True, check=True).stdout
    seen, d = {}, ""
    for line in out.splitlines():
        if line[:4].isdigit() and len(line) == 10:
            d = line
        elif line.endswith(".html"):
            seen.setdefault(Path(line).stem, d)
    return seen


def gsc(days: int) -> tuple[dict, dict]:
    S._load_env()
    site = os.getenv("GSC_SITE_URL", "https://gentlyyonder.com/")
    tok = S._session_token(REPO / os.getenv("GSC_SA_JSON", "gsc_service_account.json"))
    end = date.today() - timedelta(days=2)
    start = end - timedelta(days=days - 1)
    pages, top = {}, {}
    for r in S.gsc_query(tok, site, str(start), str(end), ["page"]):
        pages[Path(r["keys"][0].split("?")[0]).stem] = (r["impressions"], r["clicks"], r["position"])
    for r in S.gsc_query(tok, site, str(start), str(end), ["page", "query"]):
        k = Path(r["keys"][0].split("?")[0]).stem
        if r["impressions"] > top.get(k, ("", 0))[1]:
            top[k] = (r["keys"][1], r["impressions"])
    return pages, top


def ga4_clicks(days: int) -> dict[str, dict[str, float]]:
    G._load_env()
    pid = os.getenv("GA4_PROPERTY_ID")
    tok = G._session_token(REPO / (os.getenv("GA4_SA_JSON") or os.getenv("GSC_SA_JSON") or "gsc_service_account.json"))
    end = date.today()
    body = {"dateRanges": [{"startDate": (end - timedelta(days=days)).isoformat(), "endDate": end.isoformat()}],
            "dimensions": [{"name": "pagePath"}, {"name": "customEvent:partner"}],
            "metrics": [{"name": "eventCount"}], "limit": 10000,
            "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "affiliate_click"}}}}
    r = requests.post(G.API.format(pid=pid), headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=60)
    r.raise_for_status()
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for x in r.json().get("rows", []):
        path, partner = (d["value"] for d in x["dimensionValues"])
        out[E.key(path)][partner or "?"] += float(x["metricValues"][0]["value"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--new", type=int, default=28)
    a = ap.parse_args()
    notes = ["Amazon, Awin and Impact earnings are not included (no reporting API wired)."]
    try:
        gp, gq = gsc(a.days)
    except BaseException as e:  # a source that fails is reported, never guessed
        gp, gq = {}, {}; notes.append(f"Search Console not read: {type(e).__name__}")
    try:
        v = E.views(a.days)
    except BaseException as e:
        v = {}; notes.append(f"GA4 views not read: {type(e).__name__}")
    try:
        clicks = ga4_clicks(a.days)
    except BaseException as e:
        clicks = {}; notes.append(f"GA4 clicks not read: {type(e).__name__}")
    usd, n, enotes = E.earnings(a.days)
    notes += enotes
    squash = {}
    for k in list(usd):
        squash[k.replace("_", "")] = k
    new = published_since(a.new)

    rows = []
    for slug in money_pages():
        k = E.key("/articles/" + slug + ".html")
        ek = squash.get(k.replace("_", ""), k)
        imp, clk, pos = gp.get(slug, (0, 0, 0))
        c = clicks.get(k, {})
        rows.append(dict(slug=slug, imp=int(imp), gclk=int(clk), pos=pos, q=gq.get(slug, ("", 0))[0],
                         views=v.get(k, (0, ""))[0], aclk=int(sum(c.values())),
                         partners=", ".join(f"{p} {int(x)}" for p, x in sorted(c.items(), key=lambda y: -y[1])[:3]),
                         book=n.get(ek, 0), usd=usd.get(ek, 0.0), new=new.get(slug, "")))
    rows.sort(key=lambda r: (-r["usd"], -r["aclk"], -r["views"], -r["imp"]))

    def table(rs: list[dict]) -> list[str]:
        t = ["| Page | Published | Google impr | Google clicks | Avg pos | Top query | Views | Partner clicks | "
             "Top partners | Bookings | US$ |", "|---|---|---:|---:|---:|---|---:|---:|---|---:|---:|"]
        for r in rs:
            t.append(f"| {r['slug']} | {r['new'] or '-'} | {r['imp']} | {r['gclk']} | "
                     f"{r['pos']:.1f} | {r['q'][:50]} | {r['views']} | {r['aclk']} | {r['partners']} | "
                     f"{r['book']} | {r['usd']:.2f} |")
        return t

    tot = lambda f: sum(r[f] for r in rows)
    md = [f"# Money pages, last {a.days} days ({date.today()})", "",
          f"{len(rows)} pages. Google: {tot('imp'):,} impressions, {tot('gclk')} clicks. GA4: {tot('views'):,} views, "
          f"{tot('aclk')} partner clicks. Bookings: {tot('book')}, US${tot('usd'):.2f}.", ""]
    md += [f"- {x}" for x in notes] + [""]
    fresh = [r for r in rows if r["new"]]
    if fresh:
        md += [f"## Published in the last {a.new} days ({len(fresh)})", ""] + table(fresh) + [""]
    md += ["## Earning or clicked", ""] + table([r for r in rows if r["usd"] or r["aclk"]]) + [""]
    md += ["## Seen on Google, no partner click (first suspects for a verdict or title fix)", ""]
    md += table([r for r in rows if r["imp"] >= 50 and not r["aclk"]][:25]) + [""]
    out = REPO / "ga4_reports" / f"money-pages-{date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"money pages: {out.relative_to(REPO)} ({len(rows)} pages, {len(fresh)} new, "
          f"{tot('aclk')} partner clicks, US${tot('usd'):.2f})")


if __name__ == "__main__":
    main()
