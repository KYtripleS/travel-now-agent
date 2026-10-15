#!/usr/bin/env python3
"""monetization_report.py: how the money pages and components perform, from GA4.

Read-only. Writes ga4_reports/monetization-<date>.md (gitignored) with:

  - eligible-page views: page_view on pages content_classes.py marks "eligible"
  - affiliate clicks by page, partner, placement and device
  - offer funnel (promotions.py): promo_impression -> promo_click, coupon_copy
  - Stay Finder: finder_result, finder_guide_click, and affiliate clicks with
    placement "finder"

Definitions, so the rates mean one thing:
  page CTR      = affiliate_click on the page / page_view of the page
  offer CTR     = promo_click / promo_impression (an impression is half the box
                  on screen, once per offer per page view)
  finder CTR    = affiliate clicks with placement "finder" / finder_result

An affiliate click is an outbound click, not a booking. Bookings and revenue
exist only in the partners' own dashboards (Stay22, Travelpayouts, Impact,
Awin, Amazon); this report never infers them.

Event parameters such as placement and promo_id are readable here only once
they are registered as custom dimensions in GA4 (Admin > Custom definitions:
event-scoped "placement", "promo_id", "partner"). Until then the report falls
back to totals and says so.

usage: python monetization_report.py            # last 28 days
       python monetization_report.py --days 7
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import content_classes  # noqa: E402
import ga4_analyze as G  # noqa: E402

EVENTS = ["affiliate_click", "promo_impression", "promo_click", "coupon_copy",
          "finder_result", "finder_guide_click", "stay_pointer_click", "picker_click"]


def _event_rows(tok, pid, name, dims, start, end):
    """Rows for one event, or None if GA4 refuses a dimension (not registered)."""
    import requests
    body = {"dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": d} for d in dims], "metrics": [{"name": "eventCount"}],
            "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": name}}},
            "limit": 10000}
    r = requests.post(G.API.format(pid=pid), headers={"Authorization": f"Bearer {tok}"}, json=body, timeout=60)
    if r.status_code == 400:
        return None
    r.raise_for_status()
    return [([d["value"] for d in row["dimensionValues"]], G._num(row["metricValues"][0]["value"]))
            for row in r.json().get("rows", [])]


def pct(a: float, b: float) -> str:
    return f"{100 * a / b:.1f}%" if b else "n/a"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    args = ap.parse_args()
    G._load_env()
    pid = os.getenv("GA4_PROPERTY_ID")
    if not pid:
        sys.exit("GA4_PROPERTY_ID is not set (see ga4_analyze.py for setup)")
    tok = G._session_token(REPO / (os.getenv("GA4_SA_JSON") or os.getenv("GSC_SA_JSON") or "gsc_service_account.json"))
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)
    s, e = start.isoformat(), end.isoformat()
    classes = content_classes.load()
    rel = lambda path: path.lstrip("/") or "index.html"
    L = [f"# Monetisation report, {s} to {e}", "",
         "Clicks are outbound clicks, not bookings. Revenue lives in the partner dashboards.", ""]

    views = defaultdict(float)
    for d, n in _event_rows(tok, pid, "page_view", ["pagePath"], s, e) or []:
        views[d[0]] += n
    elig_views = sum(n for p, n in views.items() if classes.get(rel(p)) == "eligible")

    totals = {}
    for ev in EVENTS:
        rows = _event_rows(tok, pid, ev, ["eventName"], s, e) or []
        totals[ev] = sum(n for _, n in rows)
    L += ["## Totals", "", "| Event | Count |", "|---|---:|"]
    L += [f"| page_view on eligible pages | {elig_views:.0f} |"] + [f"| {k} | {v:.0f} |" for k, v in totals.items()]
    L += ["", f"Site-wide affiliate CTR on eligible pages: {pct(totals['affiliate_click'], elig_views)} "
          "(affiliate_click / page_view of eligible pages).",
          f"Offer CTR: {pct(totals['promo_click'], totals['promo_impression'])} (promo_click / promo_impression).", ""]

    clicks = _event_rows(tok, pid, "affiliate_click", ["pagePath", "customEvent:partner", "deviceCategory"], s, e)
    if clicks is None:
        clicks = [([p, "(partner not registered)", dev], n)
                  for (p, dev), n in ((tuple(d), n) for d, n in
                                      _event_rows(tok, pid, "affiliate_click", ["pagePath", "deviceCategory"], s, e) or [])]
    by_page, by_partner, by_device = defaultdict(float), defaultdict(float), defaultdict(float)
    for (page, partner, dev), n in clicks:
        by_page[page] += n; by_partner[partner] += n; by_device[dev] += n
    L += ["## Affiliate clicks by page", "", "| Page | Views | Clicks | CTR |", "|---|---:|---:|---:|"]
    for page, n in sorted(by_page.items(), key=lambda x: -x[1])[:30]:
        L.append(f"| {page} | {views.get(page, 0):.0f} | {n:.0f} | {pct(n, views.get(page, 0))} |")
    L += ["", "## By partner", "", "| Partner | Clicks |", "|---|---:|"]
    L += [f"| {k} | {v:.0f} |" for k, v in sorted(by_partner.items(), key=lambda x: -x[1])]
    L += ["", "## By device", "", "| Device | Clicks |", "|---|---:|"]
    L += [f"| {k} | {v:.0f} |" for k, v in sorted(by_device.items(), key=lambda x: -x[1])]

    place = _event_rows(tok, pid, "affiliate_click", ["customEvent:placement"], s, e)
    L += ["", "## By placement", ""]
    if place is None:
        L.append("Not available: register the event parameter `placement` as a custom dimension in GA4.")
    else:
        L += ["| Placement | Clicks |", "|---|---:|"] + [f"| {d[0]} | {n:.0f} |" for d, n in sorted(place, key=lambda x: -x[1])]
        finder = sum(n for d, n in place if d[0] == "finder")
        L += ["", f"Finder CTR: {pct(finder, totals['finder_result'])} (finder clicks / finder_result)."]

    promo = {}
    for ev in ("promo_impression", "promo_click", "coupon_copy"):
        rows = _event_rows(tok, pid, ev, ["customEvent:promo_id"], s, e)
        promo[ev] = None if rows is None else {d[0]: n for d, n in rows}
    L += ["", "## Offers", ""]
    if promo["promo_impression"] is None:
        L.append("Per-offer numbers need the event parameter `promo_id` registered as a custom dimension.")
    else:
        L += ["| Offer | Impressions | Clicks | CTR | Code copies |", "|---|---:|---:|---:|---:|"]
        for pid_ in sorted(set(promo["promo_impression"]) | set(promo["promo_click"] or {})):
            i, c = promo["promo_impression"].get(pid_, 0), (promo["promo_click"] or {}).get(pid_, 0)
            L.append(f"| {pid_} | {i:.0f} | {c:.0f} | {pct(c, i)} | {(promo['coupon_copy'] or {}).get(pid_, 0):.0f} |")
    out = REPO / "ga4_reports" / f"monetization-{date.today().isoformat()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L[:22]))
    print(f"\nwrote {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
