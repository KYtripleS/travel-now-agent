#!/usr/bin/env python3
"""
ceo_dashboard.py — the Daily CEO Dashboard (CEO Critical Review v2, mandate #9).

One executive report every morning: organic sessions, landing pages, Ready Score
funnel, worries, map clicks, affiliate/newsletter CTR, community contributions,
revenue trend — then rule-based Top Opportunities / Problems / Recommended Tasks.
It recommends actions; it doesn't just display numbers.

Composes the existing analyzers (gsc_analyze.py + ga4_analyze.py) — no new
infrastructure. Output: ceo_reports/ceo-YYYY-MM-DD.md (gitignored, internal).
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import gsc_analyze as G
import ga4_analyze as A

REPO = Path(__file__).resolve().parent
OUT_DIR = REPO / "ceo_reports"

EVENTS = ["worry_pick", "ready_toggle", "ready_complete", "ready_dest", "ready_style",
          "ready_link", "map_country_click", "contribute_click", "affiliate_click",
          "newsletter_click", "esim_finder_result"]


def _f(rows, i=0):
    return {r["dims"][0]: float(r["mets"][i]) for r in rows}


def main() -> None:
    G._load_env()
    import os
    site = os.environ.get("GSC_SITE_URL", "https://gentlyyonder.com/")
    sa = REPO / os.environ.get("GSC_SA_JSON", "gsc_service_account.json")
    pid = os.environ.get("GA4_PROPERTY_ID", "541637640")

    today = date.today()

    # ── GA4 (yesterday back 7d, vs prior 7d) ─────────────────────────────
    a_tok = A._session_token(sa)
    e = (today - timedelta(days=1)).isoformat()
    s = (today - timedelta(days=7)).isoformat()
    pe = (today - timedelta(days=8)).isoformat()
    ps = (today - timedelta(days=14)).isoformat()

    ch_now = _f(A.run_report(a_tok, pid, dimensions=["sessionDefaultChannelGroup"],
                             metrics=["sessions"], start=s, end=e))
    ch_prev = _f(A.run_report(a_tok, pid, dimensions=["sessionDefaultChannelGroup"],
                              metrics=["sessions"], start=ps, end=pe))
    sess_now, sess_prev = sum(ch_now.values()), sum(ch_prev.values())
    org_now = ch_now.get("Organic Search", 0)
    org_prev = ch_prev.get("Organic Search", 0)
    social_now = ch_now.get("Organic Social", 0)

    pages = A.run_report(a_tok, pid, dimensions=["landingPage"], metrics=["sessions"],
                         start=s, end=e, limit=8, order_by_metric="sessions")

    ev_rows = A.run_report(a_tok, pid, dimensions=["eventName"], metrics=["eventCount"],
                           start=s, end=e, limit=200, order_by_metric="eventCount")
    ev = {k: int(v) for k, v in _f(ev_rows).items() if k in EVENTS}
    ready_starts = ev.get("ready_dest", 0) + ev.get("ready_toggle", 0)
    completion = (100 * ev.get("ready_complete", 0) / ev["ready_dest"]) if ev.get("ready_dest") else 0.0
    aff_ctr = 100 * ev.get("affiliate_click", 0) / sess_now if sess_now else 0.0
    news_ctr = 100 * ev.get("newsletter_click", 0) / sess_now if sess_now else 0.0

    # ── GSC (3-day lag; 7d vs prior 7d) ──────────────────────────────────
    g_tok = G._session_token(sa)
    ge = (today - timedelta(days=3)).isoformat()
    gs = (today - timedelta(days=9)).isoformat()
    gpe = (today - timedelta(days=10)).isoformat()
    gps = (today - timedelta(days=16)).isoformat()
    q_now = G.rows_to_dicts(G.gsc_query(g_tok, site, gs, ge, ["query"], 500), ["query"])
    q_prev = G.rows_to_dicts(G.gsc_query(g_tok, site, gps, gpe, ["query"], 500), ["query"])
    p_now = G.rows_to_dicts(G.gsc_query(g_tok, site, gs, ge, ["page"], 200), ["page"])
    clicks_now = sum(r["clicks"] for r in q_now); clicks_prev = sum(r["clicks"] for r in q_prev)
    impr_now = sum(r["impressions"] for r in q_now); impr_prev = sum(r["impressions"] for r in q_prev)
    sd = G.striking_distance(q_now)[:5]
    near1 = G.pages_near_page1(p_now)[:5]
    risers = [r for r in G.wow_movers(q_now, q_prev)[:5]]

    # ── Demand: worry × destination (needs GA4 custom dims worry/dest) ───
    worry_rows = []
    try:
        worry_rows = A.run_report(a_tok, pid,
                                  dimensions=["customEvent:dest", "customEvent:worry"],
                                  metrics=["eventCount"], start=s, end=e, limit=30,
                                  order_by_metric="eventCount")
        worry_rows = [r for r in worry_rows
                      if r["dims"][1] not in ("", "(not set)") and r["dims"][0] not in ("", "(not set)")]
    except SystemExit:
        worry_rows = []  # dimensions not registered/propagated yet

    # ── Distribution: Reddit threads worth answering today (research only —
    #    posting stays HUMAN; automated posting kills accounts and trust) ──
    threads = []
    try:
        import requests, time as _time
        import xml.etree.ElementTree as ET
        from datetime import datetime, timezone
        NS = {"a": "http://www.w3.org/2005/Atom"}
        seen = set()
        for kw in ("esim", "cash", "suica", "first time japan"):
            try:
                r = requests.get("https://www.reddit.com/r/JapanTravelTips/search.rss",
                                 params={"q": kw, "restrict_sr": "on", "sort": "new", "t": "week"},
                                 headers={"User-Agent": "gently-yonder-dashboard/1.0"}, timeout=15)
                if r.status_code != 200 or not r.text.strip():
                    _time.sleep(3); continue
                for en in ET.fromstring(r.text).findall("a:entry", NS)[:4]:
                    link = en.find("a:link", NS).attrib.get("href", "")
                    if link in seen:
                        continue
                    seen.add(link)
                    title = (en.find("a:title", NS).text or "")[:80]
                    upd = en.find("a:updated", NS).text or ""
                    try:
                        dt = datetime.fromisoformat(upd.replace("Z", "+00:00"))
                        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    except ValueError:
                        age_h = 999
                    if age_h <= 72:
                        threads.append({"t": title, "url": link, "age": age_h, "kw": kw})
            except Exception:
                pass
            _time.sleep(3)
        threads.sort(key=lambda x: x["age"])
        threads = threads[:5]
    except Exception:
        threads = []

    # ── Community + revenue (operator-maintained local files) ────────────
    contributions = 0
    cd = REPO / "community_data"
    if cd.exists():
        for f in cd.glob("*.csv"):
            try:
                contributions += max(0, sum(1 for _ in open(f)) - 1)
            except OSError:
                pass
    # revenue: SAFE summary only — never echo raw rows (the log contains private
    # persona notes that must not spread into other files)
    subs_line = "_not measured — update data/newsletter_subs.csv weekly (date,count from Tally)_"
    subs_csv = REPO / "data" / "newsletter_subs.csv"
    if subs_csv.exists():
        try:
            rows = [r for r in csv.reader(open(subs_csv)) if r and r[0][:2] == "20"]
            if rows:
                last = rows[-1]
                delta = (f" ({int(last[1]) - int(rows[-2][1]):+d} vs prior)" if len(rows) > 1 else "")
                subs_line = f"**{last[1]}** subscribers as of {last[0]}{delta}"
        except (OSError, ValueError, IndexError):
            pass

    rev_summary = ""
    mon = REPO / "data" / "monetization_log.csv"
    if mon.exists():
        try:
            rows = list(csv.reader(open(mon)))[1:]
            paid = [r for r in rows if any("paid" == c.strip().lower() for c in r)]
            rev_summary = (f"{len(rows)} entries logged · "
                           f"{len(paid)} confirmed payout(s)" if rows else "")
        except OSError:
            pass

    # ── Rule-based opportunities / problems / tasks ──────────────────────
    opps: list[str] = []
    if sd:
        opps.append(f"Striking-distance queries ready for a push: " +
                    "; ".join(f"“{r['query']}” (pos {r['position']:.0f})" for r in sd[:3]))
    if near1:
        opps.append("Pages just off page 1 — title/FAQ/internal-link nudge: " +
                    "; ".join(r["page"].replace(site, "/")[:60] for r in near1[:3]))
    if risers:
        opps.append("Impression risers to ride: " +
                    "; ".join(f"“{r['query']}” (+{int(r['d_impr'])})" for r in risers[:3]))
    if impr_now > impr_prev * 1.3 and clicks_now <= clicks_prev:
        opps.append(f"Impressions +{100*(impr_now-impr_prev)/max(impr_prev,1):.0f}% but clicks flat — "
                    "CTR work (titles/descriptions) is the cheapest win right now.")
    if ev.get("worry_pick", 0) >= 5:
        opps.append(f"{ev['worry_pick']} worry-poll answers collected — register GA4 custom "
                    "dimensions to see WHICH worries per destination (editorial demand data).")
    opps = opps[:5]

    probs: list[str] = []
    if social_now < 5:
        probs.append(f"Organic Social ≈ {int(social_now)} sessions/wk — Pinterest still delivers "
                     "nothing; Google-dependence unhedged (v2 mistake #2).")
    if ev.get("newsletter_click", 0) == 0:
        probs.append("Zero newsletter clicks this week — the 'owned audience' hedge isn't growing.")
    if ev.get("affiliate_click", 0) == 0:
        probs.append("Zero affiliate clicks this week — revenue funnel has no top.")
    if contributions == 0:
        probs.append("0 community contributions — engine live but the '100 contributors' "
                     "milestone hasn't started; needs distribution, not features.")
    if ev.get("ready_dest", 0) and completion == 0:
        probs.append("Ready Scores get started but never completed — checklist may be too long "
                     "or items unclear.")
    if not rev_summary or "0 confirmed" in rev_summary:
        probs.append("No confirmed payouts in data/monetization_log.csv yet — log affiliate "
                     "payouts there so this report can show a revenue trend (v2 mandate #4).")
    probs = probs[:5]

    tasks: list[str] = []
    if sd:
        tasks.append(f"Harvest “{sd[0]['query']}” (pos {sd[0]['position']:.1f}) — tighten the "
                     "ranking page's title + add the query to its FAQ.")
    if impr_now > impr_prev * 1.3:
        tasks.append("Rewrite 2 titles/descriptions among the near-page-1 pages (CTR play).")
    if contributions == 0:
        tasks.append("Post one honest Reddit comment linking a genuinely relevant guide "
                     "(manual channel — first contributors come from distribution).")
    if ev.get("newsletter_click", 0) == 0:
        tasks.append("Ship one newsletter improvement (v2 #5): position it as the Weekly "
                     "Travel Prep Brief, not a footer CTA.")
    tasks = tasks[:3] if tasks else ["Ship one 20% improvement to an existing feature (v2 #7)."]

    # ── Write ─────────────────────────────────────────────────────────────
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"ceo-{today.isoformat()}.md"
    L = [f"# CEO Daily Dashboard — {today.isoformat()}",
         f"_GA4 window {s} → {e} (vs prior 7d) · GSC window {gs} → {ge}_\n",
         "## 📊 The numbers",
         f"- **Sessions:** {int(sess_now)} (prev {int(sess_prev)}) · **Organic:** {int(org_now)} "
         f"(prev {int(org_prev)}) · Social: {int(social_now)}",
         f"- **GSC:** {clicks_now} clicks (prev {clicks_prev}) · {impr_now:,} impressions "
         f"(prev {impr_prev:,})",
         f"- **Ready Score:** {ready_starts} interactions · {ev.get('ready_complete', 0)} completed "
         f"(≈{completion:.0f}% per destination-pick) · worries collected: {ev.get('worry_pick', 0)}",
         f"- **Map clicks:** {ev.get('map_country_click', 0)} · **Affiliate CTR:** {aff_ctr:.1f}% "
         f"({ev.get('affiliate_click', 0)} clicks) · **Newsletter CTR:** {news_ctr:.1f}% "
         f"({ev.get('newsletter_click', 0)})",
         f"- **Community contributions:** {contributions} (target: 25, then 100)",
         f"- **Newsletter:** {subs_line}",
         "- **Revenue log:** " + (rev_summary or "_empty — log payouts in data/monetization_log.csv_"),
         "\n## 📄 Top landing pages (7d)",
         "| Page | Sessions |", "|---|---|"]
    for r in pages:
        L.append(f"| {r['dims'][0][:70]} | {int(float(r['mets'][0]))} |")
    L.append("\n## 🎯 Distribution: threads worth answering today (value-first, no links)")
    if threads:
        for th in threads:
            L.append(f"- [{th['t']}]({th['url']}) — {th['age']:.0f}h old · matched “{th['kw']}”")
    else:
        L.append("_(no fresh matches today, or Reddit unreachable — check r/JapanTravelTips sorted by New)_")

    L.append("\n## 🧠 Demand signal: biggest worries by destination")
    if worry_rows:
        L.append("| Destination | Worry | Picks |\n|---|---|---|")
        for r in worry_rows[:10]:
            L.append(f"| {r['dims'][0]} | {r['dims'][1]} | {int(_num(r['mets'][0]))} |")
    else:
        L.append("_(collecting — custom dimensions registered 2026-07-15; rows appear as new worry_pick events arrive)_")

    L.append("\n## 🟢 Top opportunities")
    L += [f"{i+1}. {o}" for i, o in enumerate(opps)] or ["_none detected_"]
    L.append("\n## 🔴 Top problems")
    L += [f"{i+1}. {p}" for i, p in enumerate(probs)] or ["_none detected_"]
    L.append("\n## ✅ Today's recommended tasks")
    L += [f"{i+1}. {t}" for i, t in enumerate(tasks)]
    L.append("\n---\n_Rule-based recommendations from live GSC/GA4 data. "
             "Event params (worry, dest, partner) become visible once registered as "
             "GA4 event-scoped custom dimensions (Admin → Custom definitions)._")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✓ wrote {out.relative_to(REPO)}")
    print(f"  sessions {int(sess_now)} · organic {int(org_now)} · gsc {clicks_now}c/{impr_now:,}i · "
          f"ready {ready_starts} · aff {ev.get('affiliate_click', 0)} · news {ev.get('newsletter_click', 0)}")


if __name__ == "__main__":
    main()
