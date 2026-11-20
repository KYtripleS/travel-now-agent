"""Ready Score Pro sales page body, from data/pro.json (2026-11-20).

Writes the block between <!-- BEGIN rsp-body --> and <!-- END rsp-body --> in site/ and docs/
ready-score-pro.html. With checkout_url set, the button buys (GA4 begin_checkout); without it, the
button joins the waitlist. Every feature listed here must exist in products/ready-score-pro.html
(ops/build_pro_workbook.py): change both together.

usage: .venv/bin/python ops/build_pro_page.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
C = json.loads((REPO / "data" / "pro.json").read_text())

FEATURES = [
    ("A score that will not flatter you",
     "The checks that can stop a trip are marked: passport validity, the visa, the entry form or authorisation, "
     "travel insurance and the first night's bed (plus children's documents on a family trip, and business-visit "
     "rules on a work trip). Until they are done the score stays red and names them, however high the percentage."),
    ("36 destinations, with dated notes",
     "The same 36 destinations as the free Ready Score. Each one's entry step links to the official site, and "
     "Korea, the UK, Canada and the Schengen countries carry short notes with the month we checked them. Open the "
     "file more than six months later and it says so, because a downloaded file cannot update itself."),
    ("It tells you what is due",
     "Every check has a do-by date counted back from the day you leave. The workbook shows only what is due in the "
     "next two weeks, overdue first. On the trip it keeps only what is still open; back home it says the trip is done."),
    ("Passports, one per traveller",
     "Each passport is checked against your return date and the six months many countries ask for after it."),
    ("Bookings with their references",
     "Flights, rooms, trains and tours with their dates and references, earliest first, ready to print."),
    ("Estimate, then what you spent",
     "Set an estimate, log what you spend, and see what is left or how far over you are."),
    ("A packing list that starts itself",
     "One tap loads a starter list for your trip style and destination, with the right plug type. It adds only "
     "what is missing and never removes your own items."),
    ("Your own checks, and more than one trip",
     "Add checks of your own with their own do-by day, scored like the rest. Keep a separate workbook for each trip."),
    ("Yours, offline and private",
     "One file that works without internet and saves in your own browser. No account, nothing uploaded. If your "
     "browser will not save (a private window, or full storage) it tells you. A backup file restores it anywhere, "
     "and it prints to a clean plan."),
]

TABLE = [
    ("Destinations", "36", "The same 36, with dated notes"),
    ("Readiness score", "Quick on-page score", "Stays red until the checks that can stop a trip are done"),
    ("Tells you when to do each check", "No", "Yes, from your departure date"),
    ("Passports, bookings, money, packing", "No", "Yes"),
    ("Your own checks", "No", "Yes"),
    ("More than one trip", "No", "Yes"),
    ("Backup file, print, offline", "No", "Yes"),
]


def cta() -> str:
    price = C["price_usd"]
    if C.get("checkout_url"):
        url = html.escape(C["checkout_url"])
        return (f'<a class="rsp-buy" href="{url}" id="buyBtn" rel="noopener" target="_blank" '
                f'onclick="if(window.gtag)gtag(\'event\',\'begin_checkout\',{{currency:\'USD\',value:{price},'
                f'items:[{{item_id:\'ready-score-pro\',item_name:\'Ready Score Pro\',price:{price}}}]}});">'
                f'Buy Ready Score Pro, ${price} →</a>\n'
                f'<span class="rsp-price"><b>${price}</b> one-time · instant download · '
                f'{C["refund_days"]}-day refund</span>')
    url = html.escape(C["waitlist_url"])
    return (f'<a class="rsp-buy" href="{url}" id="buyBtn" rel="noopener" target="_blank" '
            f'onclick="if(window.gtag)gtag(\'event\',\'rsp_waitlist\',{{item_name:\'Ready Score Pro\'}});">'
            f'Tell me when it is on sale →</a>\n'
            f'<span class="rsp-price"><b>Opening soon</b> · ${price} one-time</span>')


def body() -> str:
    feats = "\n".join(f'<div class="rsp-feat"><h3>{html.escape(h)}</h3><p>{html.escape(p)}</p></div>'
                      for h, p in FEATURES)
    rows = "\n".join(f'<tr><td style="padding:8px 10px">{a}</td><td style="padding:8px 10px">{b}</td>'
                     f'<td style="padding:8px 10px"><b>{c}</b></td></tr>' for a, b, c in TABLE)
    th = 'style="text-align:left;padding:9px 10px;border-bottom:2px solid rgba(23,32,51,.15)"'
    return f"""<!-- BEGIN rsp-body (managed by ops/build_pro_page.py) -->
<section class="rsp-hero" id="main">
<div class="rsp-hero-in">
<p class="eyebrow">Gently Yonder · Ready Score Pro</p>
<h1>Know you are ready before you fly.</h1>
<p>Ready Score Pro is an offline trip-readiness workbook: a score that stays red until the checks that can stop a trip are done, a do-by date for every task, and one place for passports, bookings, money and packing. It saves in your browser and prints to a clean plan.</p>
<div class="rsp-cta">
{cta()}
</div>
</div>
</section>
<div class="rsp-wrap">
<p class="rsp-lead">The free <a href="index.html#ready">Ready Score</a> on our homepage gets you started. Pro is the workbook you keep for the trip you are actually taking.</p>
<div class="rsp-grid">
{feats}
</div>
</div>
<div class="rsp-wrap">
<h2 style="color:var(--navy,#172033);margin-top:34px">Free Ready Score vs Pro</h2>
<div style="overflow-x:auto">
<table style="width:100%;border-collapse:collapse;font-size:.95rem;margin:14px 0 6px">
<thead><tr><th {th}> </th><th {th}>Free</th><th {th}>Pro</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</div>
<p class="rsp-note" style="border:0;padding:0;margin:0 0 10px">If the free score is all you need, use the free score.</p>
</div>
<div class="rsp-band">
<div class="rsp-steps">
<h2 style="margin:0 0 14px;color:var(--navy,#172033)">How it works</h2>
<div class="rsp-step"><div class="num"></div><div>Buy once and download the workbook: a single file, no app, no account.</div></div>
<div class="rsp-step"><div class="num"></div><div>Open it in any browser, on a laptop or a phone, and pick your destination and dates.</div></div>
<div class="rsp-step"><div class="num"></div><div>Tick things off as you go. It saves by itself and tells you what is due next.</div></div>
<div class="rsp-step"><div class="num"></div><div>Print it or save it as a PDF to travel with.</div></div>
</div>
</div>
<div class="rsp-wrap rsp-faq">
<h2 style="color:var(--navy,#172033)">Questions</h2>
<h3>What do I receive?</h3>
<p>One HTML file that opens in any browser and works offline. Your progress stays on your own device.</p>
<h3>Will the entry rules stay accurate?</h3>
<p>Each note carries the month we checked it, and every entry step links to the official site, so confirm there for your nationality before you travel. If we publish an updated version, you can download it again from your purchase email at no cost. It is preparation guidance, not legal or immigration advice.</p>
<h3>Refunds?</h3>
<p>If it does not help you, reply to your receipt within {C["refund_days"]} days and we will refund you.</p>
<p class="rsp-note">Ready Score Pro is a one-time purchase, delivered by our checkout partner. It does not guarantee entry to any country.</p>
</div>
<!-- END rsp-body -->"""


DESC = ("Ready Score Pro is an offline trip-readiness workbook: a score that stays red until the checks that can "
        "stop a trip are done, dated notes for 36 destinations, passport, booking, money and packing trackers, "
        "and a printable plan. One-time purchase.")


def main() -> None:
    for root in ("site", "docs"):
        p = REPO / root / "ready-score-pro.html"
        s = p.read_text(encoding="utf-8")
        s = re.sub(r"<!-- BEGIN rsp-body.*?<!-- END rsp-body -->", lambda m: body(), s, flags=re.S)
        s = re.sub(r'(<meta content=")[^"]*(" name="description"/>)', lambda m: m.group(1) + DESC + m.group(2), s, 1)
        s = re.sub(r'(<meta content=")[^"]*(" name="twitter:description"/>)', lambda m: m.group(1) + DESC + m.group(2), s, 1)
        s = re.sub(r'(<meta content=")[^"]*(" property="og:description"/>)',
                   lambda m: m.group(1) + "A score that stays red until the checks that can stop a trip are done, "
                   "a do-by date for every task, and a printable plan. One-time purchase." + m.group(2), s, 1)
        p.write_text(s, encoding="utf-8")
        t = REPO / root / "ready-score-pro-thanks.html"
        ts = t.read_text(encoding="utf-8")
        ts = re.sub(r"parseFloat\(params\.get\('price'\)\)\|\|\d+", f"parseFloat(params.get('price'))||{C['price_usd']}", ts)
        t.write_text(ts, encoding="utf-8")
    print("pro page:", "on sale" if C.get("checkout_url") else "waitlist", f"${C['price_usd']}")


if __name__ == "__main__":
    main()
