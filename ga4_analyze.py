#!/usr/bin/env python3
"""
ga4_analyze.py — daily Google Analytics 4 (session) analysis for Gently Yonder.

The companion to gsc_analyze.py. GSC measures *search* (impressions/clicks);
GA4 measures *sessions* — actual visits from every channel (Google, Pinterest,
Reddit, direct…). This is the metric for the "50k sessions/month by October"
goal, and the only way to see whether Pinterest is actually sending traffic.

Writes a dated Markdown report to ga4_reports/ with: total sessions + run-rate
vs the 50k target, the daily trend, the **channel mix** (Organic Search vs
Organic Social/Pinterest vs Direct vs Referral), top sources, and top landing
pages.

Auth: reuses the SAME Google **service account** as gsc_analyze.py. One-time
setup by the operator:

  1. Google Cloud Console → same project → APIs & Services → Library →
     enable "Google Analytics Data API".
  2. In GA4 (https://analytics.google.com) → Admin → Property → Property Access
     Management → add the service account's email
     (…@….iam.gserviceaccount.com) with the "Viewer" role.
  3. Find the numeric **Property ID** in GA4 Admin → Property Settings
     (a number like 123456789 — NOT the "G-XXXX" measurement id).
  4. In .env add:   GA4_PROPERTY_ID=123456789
     (reuses GSC_SA_JSON=gsc_service_account.json; set GA4_SA_JSON to override.)

Then:  python ga4_analyze.py            # last 28 days
       python ga4_analyze.py --days 7
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent
REPORT_DIR = REPO / "ga4_reports"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
API = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"
TARGET_SESSIONS = 50_000  # north-star for this push

SETUP = __doc__.split("Auth:")[1].strip()


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env")
    except Exception:
        pass


def _session_token(sa_json: Path) -> str:
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except ImportError:
        sys.exit("Missing dependency: pip install google-auth")
    creds = service_account.Credentials.from_service_account_file(
        str(sa_json), scopes=SCOPES)
    creds.refresh(Request())
    return creds.token


def run_report(token: str, pid: str, *, dimensions: list[str], metrics: list[str],
               start: str, end: str, limit: int = 100,
               order_by_metric: str | None = None) -> list[dict]:
    import requests
    body: dict = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": d} for d in dimensions],
        "metrics": [{"name": m} for m in metrics],
        "limit": limit,
    }
    if order_by_metric:
        body["orderBys"] = [{"metric": {"metricName": order_by_metric}, "desc": True}]
    url = API.format(pid=pid)
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json=body, timeout=60)
    if r.status_code == 403:
        sys.exit("403 from GA4 Data API. Check: API enabled + service-account "
                 "added as Viewer on the property + correct GA4_PROPERTY_ID.\n\n" + SETUP)
    if r.status_code == 400:
        sys.exit(f"400 from GA4: {r.text[:400]}")
    r.raise_for_status()
    rows = []
    for row in r.json().get("rows", []):
        dims = [d["value"] for d in row.get("dimensionValues", [])]
        mets = [m["value"] for m in row.get("metricValues", [])]
        rows.append({"dims": dims, "mets": mets})
    return rows


def _num(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description="GA4 session analysis for Gently Yonder.")
    ap.add_argument("--days", type=int, default=28)
    args = ap.parse_args()

    _load_env()
    pid = os.getenv("GA4_PROPERTY_ID")
    if not pid:
        sys.exit("GA4_PROPERTY_ID missing from .env.\n\n" + SETUP)
    sa = os.getenv("GA4_SA_JSON") or os.getenv("GSC_SA_JSON") or "gsc_service_account.json"
    sa_path = (REPO / sa) if not os.path.isabs(sa) else Path(sa)
    if not sa_path.exists():
        sys.exit(f"Service-account JSON not found: {sa_path}\n\n" + SETUP)

    token = _session_token(sa_path)
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=args.days - 1)
    s, e = start.isoformat(), end.isoformat()

    # 1) daily trend (totals summed from the date dimension)
    trend = run_report(token, pid, dimensions=["date"],
                       metrics=["sessions", "totalUsers", "engagedSessions"],
                       start=s, end=e, limit=400)
    trend.sort(key=lambda r: r["dims"][0])
    total_sessions = sum(_num(r["mets"][0]) for r in trend)
    total_users = sum(_num(r["mets"][1]) for r in trend)
    engaged = sum(_num(r["mets"][2]) for r in trend)
    per_day = total_sessions / max(args.days, 1)
    run_rate = per_day * 30

    # 2) channel mix
    channels = run_report(token, pid, dimensions=["sessionDefaultChannelGroup"],
                          metrics=["sessions", "engagedSessions"],
                          start=s, end=e, limit=50, order_by_metric="sessions")
    # 3) top sources
    sources = run_report(token, pid, dimensions=["sessionSource", "sessionMedium"],
                         metrics=["sessions"], start=s, end=e, limit=15,
                         order_by_metric="sessions")
    # 4) top landing pages
    pages = run_report(token, pid, dimensions=["landingPage"],
                       metrics=["sessions"], start=s, end=e, limit=20,
                       order_by_metric="sessions")
    # 5) moat & funnel custom events
    OUR_EVENTS = ["worry_pick", "ready_toggle", "ready_complete", "ready_dest",
                  "ready_style", "ready_link", "map_country_click",
                  "contribute_click", "affiliate_click", "newsletter_click",
                  "esim_finder_result"]
    events = run_report(token, pid, dimensions=["eventName"], metrics=["eventCount"],
                        start=s, end=e, limit=200, order_by_metric="eventCount")
    events = [r for r in events if r["dims"][0] in OUR_EVENTS]

    REPORT_DIR.mkdir(exist_ok=True)
    out = REPORT_DIR / f"ga4-{e}.md"
    L = []
    L.append(f"# GA4 sessions report — {e}\n")
    L.append(f"**Property:** {pid}  ·  **Window:** {s} → {e} ({args.days}d)\n")
    L.append(f"**Sessions:** {int(total_sessions):,} · **Users:** {int(total_users):,} "
             f"· **Engaged:** {int(engaged):,} · **~{per_day:.0f}/day**\n")
    pct = 100 * run_rate / TARGET_SESSIONS
    bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
    L.append(f"## 🎯 Progress to 50k sessions/month")
    L.append(f"Run-rate (last {args.days}d × 30): **{int(run_rate):,} / 50,000**  ({pct:.1f}%)")
    L.append(f"`{bar}`  — {'on the board, keep stacking channels' if run_rate < 50000 else 'TARGET HIT 🎉'}\n")

    L.append("## 📡 Channel mix (where sessions come from)")
    L.append("Watch **Organic Social** (Pinterest) — that's the 50k engine.\n")
    L.append("| Channel | Sessions | Engaged |\n|---|---|---|")
    for r in channels:
        L.append(f"| {r['dims'][0]} | {int(_num(r['mets'][0])):,} | {int(_num(r['mets'][1])):,} |")

    L.append("\n## 🔗 Top sources / medium")
    L.append("| Source / Medium | Sessions |\n|---|---|")
    for r in sources:
        L.append(f"| {r['dims'][0]} / {r['dims'][1]} | {int(_num(r['mets'][0])):,} |")

    L.append("\n## 📄 Top landing pages")
    L.append("| Landing page | Sessions |\n|---|---|")
    for r in pages:
        L.append(f"| {r['dims'][0]} | {int(_num(r['mets'][0])):,} |")

    L.append("\n## 🧭 Moat & funnel events (custom)")
    L.append("ready_complete = Ready Scores completed · worry_pick = demand signal · "
             "affiliate_click = revenue funnel · newsletter_click = Google hedge.\n")
    if events:
        L.append("| Event | Count |\n|---|---|")
        for r in events:
            L.append(f"| {r['dims'][0]} | {int(_num(r['mets'][0])):,} |")
    else:
        L.append("_(no custom events in this window yet — instrumentation went live 2026-07-13)_")

    L.append("\n## 📈 Daily sessions")
    L.append("| Date | Sessions | Users |\n|---|---|---|")
    for r in trend:
        d = r["dims"][0]
        d = f"{d[:4]}-{d[4:6]}-{d[6:]}"
        L.append(f"| {d} | {int(_num(r['mets'][0]))} | {int(_num(r['mets'][1]))} |")

    L.append("\n---\n_Generated by ga4_analyze.py. GA4 data is usually complete within ~24–48h._")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✓ wrote {out.relative_to(REPO)}  ({int(total_sessions):,} sessions, "
          f"run-rate {int(run_rate):,}/mo = {pct:.1f}% of 50k)")


if __name__ == "__main__":
    main()
