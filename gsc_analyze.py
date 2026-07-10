#!/usr/bin/env python3
"""
gsc_analyze.py — daily Google Search Console analysis for Gently Yonder.

Pulls Search Analytics data via the GSC API and writes a dated Markdown report
with the things worth acting on: striking-distance keywords (nearly page 1),
high-impression / low-CTR pages (title & meta opportunities), week-over-week
risers, top queries and pages, and the clicks/impressions trend.

Auth: a Google **service account** (no interactive login — ideal for a daily
cron). One-time setup by the operator:

  1. Google Cloud Console → create/pick a project → APIs & Services → Library →
     enable "Google Search Console API".
  2. APIs & Services → Credentials → Create credentials → Service account.
     Give it a name; no roles needed. Open it → Keys → Add key → JSON → download.
  3. Save that JSON as  gsc_service_account.json  in this repo folder
     (it is gitignored; never commit it).
  4. In Search Console (https://search.google.com/search-console) → Settings →
     Users and permissions → Add user → paste the service account's email
     (…@….iam.gserviceaccount.com) → permission "Full" (or "Restricted").
  5. In .env add:   GSC_SITE_URL=https://gentlyyonder.com/
     (optional)     GSC_SA_JSON=gsc_service_account.json

Then:  python gsc_analyze.py            # last 28 days
       python gsc_analyze.py --days 90
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

REPO = Path(__file__).resolve().parent
REPORT_DIR = REPO / "gsc_reports"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
API = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"

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


def gsc_query(token: str, site: str, start: str, end: str,
              dimensions: list[str], row_limit: int = 25000,
              filters: list[dict] | None = None) -> list[dict]:
    import requests
    body = {"startDate": start, "endDate": end, "dimensions": dimensions,
            "rowLimit": row_limit, "dataState": "all"}
    if filters:
        body["dimensionFilterGroups"] = [{"filters": filters}]
    url = API.format(site=quote(site, safe=""))
    r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                      json=body, timeout=60)
    if r.status_code != 200:
        sys.exit(f"GSC API {r.status_code}: {r.text[:300]}")
    return r.json().get("rows", [])


def rows_to_dicts(rows: list[dict], keys: list[str]) -> list[dict]:
    out = []
    for row in rows:
        d = {k: row["keys"][i] for i, k in enumerate(keys)}
        d.update(clicks=row.get("clicks", 0), impressions=row.get("impressions", 0),
                 ctr=row.get("ctr", 0.0), position=row.get("position", 0.0))
        out.append(d)
    return out


# ── analyses ────────────────────────────────────────────────────────────────

def striking_distance(queries: list[dict], min_impr=20, lo=4.5, hi=20.0) -> list[dict]:
    """Queries just off page 1 / just off the top — the fastest wins."""
    c = [q for q in queries if lo <= q["position"] <= hi and q["impressions"] >= min_impr]
    return sorted(c, key=lambda q: q["impressions"], reverse=True)[:25]


def low_ctr(queries: list[dict], min_impr=80, max_ctr=0.02, max_pos=15) -> list[dict]:
    """Ranking well with lots of impressions but few clicks — title/meta rewrite."""
    c = [q for q in queries if q["impressions"] >= min_impr
         and q["ctr"] < max_ctr and q["position"] <= max_pos]
    return sorted(c, key=lambda q: q["impressions"], reverse=True)[:25]


def wow_movers(recent: list[dict], prior: list[dict], key="query"):
    pr = {q[key]: q for q in prior}
    ups = []
    for q in recent:
        p = pr.get(q[key])
        d_impr = q["impressions"] - (p["impressions"] if p else 0)
        d_clk = q["clicks"] - (p["clicks"] if p else 0)
        ups.append({**q, "d_impr": d_impr, "d_clk": d_clk, "is_new": p is None})
    risers = sorted(ups, key=lambda q: q["d_impr"], reverse=True)[:20]
    return risers


# ── report ──────────────────────────────────────────────────────────────────

def _tbl(rows: list[dict], cols: list[tuple[str, str]]) -> str:
    if not rows:
        return "_(none)_\n"
    head = "| " + " | ".join(h for _, h in cols) + " |\n"
    head += "|" + "|".join("---" for _ in cols) + "|\n"
    body = ""
    for r in rows:
        cells = []
        for k, _ in cols:
            v = r[k]
            if k == "ctr":
                v = f"{v*100:.1f}%"
            elif k == "position":
                v = f"{v:.1f}"
            elif k in ("clicks", "impressions", "d_impr", "d_clk"):
                v = f"{int(round(v)):+}" if k.startswith("d_") else f"{int(round(v))}"
            elif k in ("query", "page"):
                v = str(v).replace("|", "\\|")[:70]
            cells.append(str(v))
        body += "| " + " | ".join(cells) + " |\n"
    return head + body


def build_report(site: str, start: str, end: str, queries: list[dict],
                 pages: list[dict], trend: list[dict], risers: list[dict]) -> str:
    tot_c = sum(q["clicks"] for q in queries)
    tot_i = sum(q["impressions"] for q in queries)
    ctr = (tot_c / tot_i) if tot_i else 0
    avg_pos = (sum(q["position"] * q["impressions"] for q in queries) / tot_i) if tot_i else 0
    QCOLS = [("query", "Query"), ("clicks", "Clk"), ("impressions", "Impr"),
             ("ctr", "CTR"), ("position", "Pos")]
    PCOLS = [("page", "Page"), ("clicks", "Clk"), ("impressions", "Impr"),
             ("ctr", "CTR"), ("position", "Pos")]
    RCOLS = [("query", "Query"), ("d_impr", "ΔImpr"), ("d_clk", "ΔClk"),
             ("impressions", "Impr"), ("position", "Pos")]
    sd, lc = striking_distance(queries), low_ctr(queries)
    top_q = sorted(queries, key=lambda q: q["clicks"], reverse=True)[:20]
    top_p = sorted(pages, key=lambda q: q["clicks"], reverse=True)[:20]

    md = f"""# GSC report — {end}

**Property:** {site}  ·  **Window:** {start} → {end}
**Totals:** {int(tot_c)} clicks · {int(tot_i)} impressions · {ctr*100:.1f}% CTR · avg pos {avg_pos:.1f}

## 🎯 Striking distance (pos {4.5}–20, act on these first)
Queries you already rank for that a small push could move onto page 1 / into the top.
Add/expand a section, tighten the title, add an FAQ, or build an internal link.

{_tbl(sd, QCOLS)}
## 📝 High impressions, low CTR (rewrite title & meta description)
You rank but few click — usually a title/description problem.

{_tbl(lc, QCOLS)}
## 📈 Week-over-week risers (ride the momentum)
Biggest impression gains vs the previous 7 days (★ = newly appearing).

{_tbl([{**r, "query": ("★ " if r["is_new"] else "") + r["query"]} for r in risers], RCOLS)}
## 🏆 Top queries (by clicks)

{_tbl(top_q, QCOLS)}
## 📄 Top pages (by clicks)

{_tbl(top_p, PCOLS)}
## Daily trend (clicks · impressions)

{_tbl(sorted(trend, key=lambda d: d['date']), [("date","Date"),("clicks","Clk"),("impressions","Impr"),("position","Pos")])}
---
_Generated by gsc_analyze.py. Data lags GSC by ~2–3 days._
"""
    return md


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--site", default=None)
    args = ap.parse_args()
    _load_env()

    site = args.site or os.getenv("GSC_SITE_URL", "https://gentlyyonder.com/")
    sa_json = REPO / os.getenv("GSC_SA_JSON", "gsc_service_account.json")
    if not sa_json.exists():
        print("⚠️  Service-account key not found — GSC not connected yet.\n"
              f"    Expected at: {sa_json}\n\n=== ONE-TIME SETUP ===\n{SETUP}")
        sys.exit(1)

    end = date.today() - timedelta(days=2)          # GSC freshness lag
    start = end - timedelta(days=args.days - 1)
    p7_end = end - timedelta(days=7)
    p7_start = p7_end - timedelta(days=6)
    r7_start = end - timedelta(days=6)

    token = _session_token(sa_json)
    print(f"Querying {site}  {start} → {end} …", flush=True)
    queries = rows_to_dicts(gsc_query(token, site, str(start), str(end), ["query"]), ["query"])
    pages = rows_to_dicts(gsc_query(token, site, str(start), str(end), ["page"]), ["page"])
    trend = rows_to_dicts(gsc_query(token, site, str(start), str(end), ["date"]), ["date"])
    recent7 = rows_to_dicts(gsc_query(token, site, str(r7_start), str(end), ["query"]), ["query"])
    prior7 = rows_to_dicts(gsc_query(token, site, str(p7_start), str(p7_end), ["query"]), ["query"])
    risers = wow_movers(recent7, prior7)

    md = build_report(site, str(start), str(end), queries, pages, trend, risers)
    REPORT_DIR.mkdir(exist_ok=True)
    out = REPORT_DIR / f"gsc-{end}.md"
    out.write_text(md, encoding="utf-8")
    print(f"✓ wrote {out.relative_to(REPO)}  "
          f"({len(queries)} queries, {len(pages)} pages)")
    # brief console summary
    sd = striking_distance(queries)[:5]
    if sd:
        print("\nTop striking-distance opportunities:")
        for q in sd:
            print(f"  pos {q['position']:.1f}  {int(q['impressions'])} impr  "
                  f"{q['ctr']*100:.1f}% CTR  — {q['query']}")


if __name__ == "__main__":
    main()
