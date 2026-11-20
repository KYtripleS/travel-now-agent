"""Earnings per 1,000 page views, by page (2026-11-20: measure money, not traffic).

Joins three read-only sources on one page key (the slug that js/gy-reveal.js puts in every
partner link's sub id):
  - GA4 page views per page (ga4_analyze.run_report, same service account)
  - Travelpayouts commission per page (sub_id "<page>__<placement>", ops/tp_sales.actions)
  - Stay22 commission per page (campaign "<page>__<placement>" or "<page>_map")

Amazon, Awin and Impact (Holafly) have no reporting API wired here, so their earnings are
missing: say so wherever the numbers are quoted. A pending booking counts at its listed
commission; cancelled ones are left out.

Writes ga4_reports/epc-<date>.md (gitignored) with:
  - every page that earned, ranked by EPC
  - pages with the most views and no earnings: rewrite or merge candidates
  - the 20 money pages to concentrate on (earnings first, then views, eligible pages only)

usage: .venv/bin/python ops/epc.py [--days 90]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ops"))
import ga4_analyze as G  # noqa: E402
import content_classes as CC  # noqa: E402


def key(page: str) -> str:
    """The page key as gy-reveal.js builds it, then reduced to letters, digits and _."""
    page = re.sub(r"^/(travel-now-agent/)?(articles/)?", "", page.split("?")[0])
    page = re.sub(r"(/index)?\.html$|/$", "", page) or "home"
    return re.sub(r"[^A-Za-z0-9]+", "_", page).strip("_").lower()


PLACEMENTS = ("verdict", "hotelname", "photobtn", "plans", "table", "section", "pick", "hotel", "city",
              "quickpick", "globe", "promo", "stickybar", "finder", "widget", "prose", "map", "tpwidget",
              "flightmap")


def strip_placement(sub: str) -> str:
    """Sub ids collapse "__" to "_", so the placement is the last known word, if any."""
    sub = re.sub(r"^gentlyyonder_", "", sub.lower())
    for pl in sorted(PLACEMENTS, key=len, reverse=True):
        for suf in ("_" + pl, "_" + pl.replace("_", "")):
            if sub.endswith(suf):
                return sub[: -len(suf)]
    return sub


def views(days: int) -> dict[str, tuple[int, str]]:
    G._load_env()
    pid = os.getenv("GA4_PROPERTY_ID")
    sa = REPO / os.getenv("GA4_SA_JSON", os.getenv("GSC_SA_JSON", "gsc_service_account.json"))
    tok = G._session_token(sa)
    end = date.today()
    rows = G.run_report(tok, pid, dimensions=["pagePath"], metrics=["screenPageViews"],
                        start=(end - timedelta(days=days)).isoformat(), end=end.isoformat(),
                        limit=5000, order_by_metric="screenPageViews")
    out: dict[str, tuple[int, str]] = {}
    for r in rows:
        path, n = r["dims"][0], int(G._num(r["mets"][0]))
        k = key(path)
        prev = out.get(k, (0, path))
        out[k] = (prev[0] + n, prev[1] if prev[0] >= n else path)
    return out


def earnings(days: int) -> tuple[dict[str, float], dict[str, int], list[str]]:
    usd: dict[str, float] = defaultdict(float)
    n: dict[str, int] = defaultdict(int)
    notes = []
    since = (date.today() - timedelta(days=days)).isoformat()
    try:
        import tp_sales
        for x in tp_sales.actions(since):
            got = float(x.get("paid_profit_usd") or 0)
            if not (x.get("state") or float(x.get("price_usd") or 0) > 0) or x.get("state") == "cancelled":
                continue
            k = strip_placement(x["sub_id"]) if x.get("sub_id") else "(no sub id)"
            usd[k] += got
            n[k] += 1
    except Exception as e:  # a source that fails is reported, never guessed
        notes.append(f"Travelpayouts not read: {type(e).__name__}")
    try:
        import stay22_report as S
        for t in S.transactions(since, date.today().isoformat()):
            if str(t.get("bookingStatus", "")).lower().startswith("cancel"):
                continue
            page, _ = S.split(t.get("campaignId") or "")
            k = strip_placement(key(page)) if page else "(no campaign)"
            usd[k] += float(t.get("commission") or 0)
            n[k] += 1
    except SystemExit as e:
        notes.append(f"Stay22 not read: {e}")
    except Exception as e:
        notes.append(f"Stay22 not read: {type(e).__name__}")
    return usd, n, notes


def eligible_keys() -> set[str]:
    return {key("/" + rel) for rel, cls in CC.load().items() if cls == "eligible"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90)
    a = ap.parse_args()
    v = views(a.days)
    usd, n, notes = earnings(a.days)
    squash = {k.replace("_", ""): k for k in v}
    for k in [k for k in usd if k not in v and k.replace("_", "") in squash]:
        real = squash[k.replace("_", "")]
        usd[real] += usd.pop(k)
        n[real] += n.pop(k)
    elig = eligible_keys()
    total_v = sum(x[0] for x in v.values())
    total_usd = sum(usd.values())
    L = [f"# EPC by page, last {a.days} days ({date.today()})", "",
         "EPC = commission in US$ per 1,000 page views. Travelpayouts + Stay22 only: Amazon, Awin and "
         "Impact (Holafly) earnings are not in these numbers.", "",
         f"Page views: {total_v:,}. Commission: US${total_usd:,.2f} on {sum(n.values())} bookings. "
         f"Site EPC: US${(total_usd / total_v * 1000 if total_v else 0):.2f}.", ""]
    L += [f"- {x}" for x in notes] + ([""] if notes else [])
    L += ["## Pages that earned", "", "| Page | Views | Bookings | US$ | EPC |", "|---|---:|---:|---:|---:|"]
    for k in sorted(usd, key=lambda k: -(usd[k] / max(v.get(k, (0,))[0], 1))):
        vw = v.get(k, (0, ""))[0]
        L.append(f"| {k} | {vw:,} | {n[k]} | {usd[k]:,.2f} | {usd[k] / vw * 1000 if vw else float('nan'):.2f} |")
    L += ["", "## Most-viewed pages with no earnings (rewrite, re-link or merge)", "",
          "| Page | Views |", "|---|---:|"]
    zero = [(k, x[0]) for k, x in v.items() if k not in usd and k in elig]
    for k, vw in sorted(zero, key=lambda t: -t[1])[:25]:
        L.append(f"| {k} | {vw:,} |")
    L += ["", "## The 20 money pages (earnings first, then views; eligible pages only)", ""]
    ranked = sorted((k for k in set(v) | set(usd) if k in elig),
                    key=lambda k: (-usd.get(k, 0), -v.get(k, (0,))[0]))[:20]
    for i, k in enumerate(ranked, 1):
        L.append(f"{i}. {k}: {v.get(k, (0,))[0]:,} views, US${usd.get(k, 0):,.2f}")
    out = REPO / "ga4_reports" / f"epc-{date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(L) + "\n")
    print(f"epc: {out.relative_to(REPO)} ({len(usd)} earning pages, site EPC "
          f"US${(total_usd / total_v * 1000 if total_v else 0):.2f})")


if __name__ == "__main__":
    main()
