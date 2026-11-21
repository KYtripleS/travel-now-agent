"""Open data page (2026-11-21): publish the fact ledger so writers, researchers and AI tools can cite it.

An outside review said the site will not be treated as a primary source until others cite it. The ledger
(data/facts/*.json) is the one thing we have that nobody else has: every fact behind our guides, with its
source and the date we checked it. This publishes it, free to reuse with a link (CC BY 4.0).

Writes:
  site/data/fact-ledger.json, site/data/fact-ledger.csv   (and docs/)
  site/open-data.html                                    (and docs/), added to the sitemap

Left out on purpose: evidence quotes copied from source pages (their text is the source's, not ours),
superseded facts, and the internal "watch" settings.

usage: .venv/bin/python ops/build_open_data.py
"""
from __future__ import annotations

import csv
import html
import io
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import build_library as L  # noqa: E402

SITE = "https://gentlyyonder.com/"
URL = SITE + "open-data.html"
TOPIC = {"hotel": "Hotels (open, address, distances)", "transport": "Transport and routes", "place": "Places and venues",
         "tax": "Taxes and fees", "fare": "Fares", "price": "Prices", "entry": "Entry rules", "history": "History",
         "stat": "Statistics"}


def rows() -> list[dict]:
    out = []
    for f in sorted((REPO / "data" / "facts").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for x in d["facts"]:
            if x.get("status") == "superseded" or x.get("superseded_by"):
                continue
            out.append({
                "id": x["id"], "place": d.get("place", f.stem), "topic": x.get("topic", ""),
                "claim": x["claim"], "value": x.get("value"),
                "sources": [{"url": s.get("url", ""), "title": s.get("title", ""), "kind": s.get("kind", "")}
                            for s in x.get("sources", [])],
                "checked": x.get("checked", ""), "recheck_days": x.get("recheck_days"),
                "note": x.get("note", ""),
                "pages": sorted(SITE + p for p in (x.get("used_in") or {})),
            })
    return out


def to_csv(data: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "place", "topic", "claim", "checked", "source_urls", "source_kinds", "note", "used_on_pages"])
    for r in data:
        w.writerow([r["id"], r["place"], r["topic"], r["claim"], r["checked"],
                    " | ".join(s["url"] for s in r["sources"]), " | ".join(s["kind"] for s in r["sources"]),
                    r["note"], " | ".join(r["pages"])])
    return buf.getvalue()


def render(data: list[dict], version: str) -> str:
    n = len(data)
    places = Counter(r["place"] for r in data)
    topics = Counter(r["topic"] for r in data)
    official = sum(1 for r in data if any(s["kind"] in ("official", "operator") for s in r["sources"]))
    checked = sorted(r["checked"] for r in data if r["checked"])
    since = (date.today().replace(day=1)).isoformat()[:7]
    recent = sum(1 for c in checked if c[:7] >= since)
    pct = round(100 * official / n)
    topic_rows = "\n".join(f"<tr><td>{html.escape(TOPIC.get(t, t.title()))}</td><td>{c:,}</td></tr>"
                           for t, c in topics.most_common())
    place_list = ", ".join(html.escape(p) for p, _ in sorted(places.items()))
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "Dataset", "name": "Gently Yonder travel fact ledger",
        "description": (f"{n:,} travel-preparation facts (hotels, transport, fares, taxes, entry rules) for "
                        f"{len(places)} countries and cities, each with its source and the date it was last checked."),
        "url": URL, "version": version, "dateModified": version, "isAccessibleForFree": True,
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Organization", "name": "Gently Yonder", "url": SITE},
        "keywords": ["travel", "tourist tax", "entry requirements", "fares", "hotels", "fact checking"],
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": SITE + "data/fact-ledger.json"},
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": SITE + "data/fact-ledger.csv"}],
    }, ensure_ascii=False)
    desc = (f"Download the {n:,} facts behind our travel guides, each with its source and the date we checked it. "
            "Free to reuse with a link (CC BY 4.0).")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Open data: the fact ledger behind our guides | Gently Yonder</title>
<meta name="description" content="{html.escape(desc)}" />
<link rel="canonical" href="{URL}" />
<meta name="robots" content="index, follow" />
<meta property="og:title" content="Open data: the fact ledger behind our guides" />
<meta property="og:description" content="{html.escape(desc)}" />
<meta property="og:url" content="{URL}" />
<link rel="stylesheet" href="style-v2.css" />
<script type="application/ld+json">{ld}</script>
{L.GA4}
<!-- BEGIN favicon (managed by add_favicon.py) -->
<link href="/favicon.svg" rel="icon" type="image/svg+xml"/>
<link href="/favicon-48.png" rel="icon" sizes="48x48" type="image/png"/>
<link href="/favicon-192.png" rel="icon" sizes="192x192" type="image/png"/>
<link href="/apple-touch-icon.png" rel="apple-touch-icon"/>
<!-- END favicon -->
</head>
<body>
{L._nav_block("")}
<header class="hero article-hero">
<p class="label">Open data</p>
<h1>The fact ledger behind our guides</h1>
</header>
<main id="main">
<section class="article">
<p class="article-lede">Every price, fare, tax, opening and entry rule in our guides sits in one ledger, with
the page it came from and the day we last checked it. Here it is: {n:,} facts for {len(places)} countries and
cities, free to download and reuse with a link.</p>
<h2>Download</h2>
<ul>
<li><a href="data/fact-ledger.csv" download>fact-ledger.csv</a>: one row per fact, sources and pages joined with " | ".</li>
<li><a href="data/fact-ledger.json" download>fact-ledger.json</a>: the same facts, with structured values where we hold them.</li>
<li><a href="data/tourist-taxes-2026.csv" download>tourist-taxes-2026.csv</a>: the tourist, city and hotel tax rules
behind our <a href="articles/tourist-taxes-around-the-world-2026-data.html">tourist taxes data report</a>.</li>
</ul>
<p>Version {version}. The files are rebuilt every time we publish, so a fact we recheck or correct changes here too.</p>
<h2>What is in it</h2>
<p>{pct}% of the facts cite the official body, the operator or the venue itself; the rest cite news reports or
reference works, and the source kind is in every row. {recent:,} facts were checked this month. Each row has:</p>
<ul>
<li><strong>claim</strong>: the fact, in the words our guides use;</li>
<li><strong>sources</strong>: the page or pages it rests on, and what kind of source each is;</li>
<li><strong>checked</strong>: the day we last confirmed it against that source;</li>
<li><strong>note</strong>: what we could not confirm, or how we worked something out, when that matters;</li>
<li><strong>pages</strong>: our guides that state it.</li>
</ul>
<div style="overflow-x:auto">
<table style="border-collapse:collapse;margin:10px 0 6px">
<thead><tr><th style="text-align:left;padding:6px 14px 6px 0">Topic</th><th style="text-align:left;padding:6px 0">Facts</th></tr></thead>
<tbody>
{topic_rows}
</tbody>
</table>
</div>
<p>Places: {place_list}.</p>
<h2>How we keep it current</h2>
<p>Each fact has a recheck date. When it comes round we open the source again; if the fact has changed we fix
every guide that states it and log the fix on our <a href="corrections.html">corrections page</a>.
<a href="methodology.html">How we verify</a> explains the method.</p>
<h2>How to cite it</h2>
<p>Reuse it however you like, in articles, research or software, as long as you link to this page
(<a href="https://creativecommons.org/licenses/by/4.0/" rel="noopener" target="_blank">CC BY 4.0</a>). Suggested citation:</p>
<p><code>Gently Yonder ({version[:4]}). Travel fact ledger, version {version}. {URL}</code></p>
<p>If you find a fact that is wrong or out of date, <a href="contact.html">tell us</a> and we will correct it in
public.</p>
<h2>Limits</h2>
<p>Facts age. Use the checked date, and confirm anything that decides a booking, a payment or an entry with the
source before you rely on it. Entry rules here are preparation guidance, not legal or immigration advice.</p>
<p class="back-link"><a href="about.html">&larr; About Gently Yonder</a></p>
</section>
</main>
{L._footer_block("")}
<script defer src="js/gy-reveal.js"></script>
</body>
</html>
"""


def main() -> None:
    data = rows()
    version = max(r["checked"] for r in data if r["checked"])
    js = json.dumps({"name": "Gently Yonder travel fact ledger", "version": version, "license": "CC BY 4.0",
                     "cite": URL, "count": len(data), "facts": data}, ensure_ascii=False, indent=1)
    cs = to_csv(data)
    page = render(data, version)
    for root in (REPO / "site", REPO / "docs"):
        (root / "data" / "fact-ledger.json").write_text(js, encoding="utf-8")
        (root / "data" / "fact-ledger.csv").write_text(cs, encoding="utf-8")
        (root / "open-data.html").write_text(page, encoding="utf-8")
        sm = root / "sitemap.xml"
        s = sm.read_text(encoding="utf-8")
        if f"<loc>{URL}</loc>" not in s:
            s = s.replace("</urlset>", f"  <url>\n    <loc>{URL}</loc>\n    <changefreq>weekly</changefreq>\n"
                                       f"    <priority>0.6</priority>\n  </url>\n</urlset>")
            sm.write_text(s, encoding="utf-8")
    print(f"open data: {len(data)} facts, version {version}")


if __name__ == "__main__":
    main()
