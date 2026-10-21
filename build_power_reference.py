#!/usr/bin/env python3
"""
build_power_reference.py

Builds the travel-power hub: plug types, voltage and frequency for 216
countries and territories, with an adapter checker, plus the same data as
CSV and JSON for anyone who wants to reuse it.

Data: programmatic/plugs_world.csv. Plug types, voltage and frequency are the
IEC World Plugs listing (iec.ch/world-plugs, retired in 2026; read from the
web.archive.org copy of 19 January 2026, which matches 28 November 2025).
`also_reported` holds plug types that Wikipedia's "Mains electricity by
country" lists and the IEC does not. `page` is the slug of our own country
guide, when there is one. Edit the CSV, then re-run.

Outputs (site/ and docs/):
  travel-power/index.html
  data/travel-power.json, data/travel-power.csv
  js/gy-power.js is hand-written; this script does not touch it.

Usage: .venv/bin/python build_power_reference.py
"""

from __future__ import annotations

import csv
import html
import json
import shutil
from pathlib import Path

from add_ga4 import snippet as ga4_snippet

REPO = Path(__file__).resolve().parent
CSV_PATH = REPO / "programmatic" / "plugs_world.csv"
URL = "https://gentlyyonder.com/travel-power/"
CHECKED = "21 October 2026"
CHECKED_ISO = "2026-10-21"
IEC_ARCHIVE = "https://web.archive.org/web/20260119122348/https://www.iec.ch/world-plugs"
WIKI = "https://en.wikipedia.org/wiki/Mains_electricity_by_country"

# Plug types, in our words. Sockets a plug fits are what the checker uses (js/gy-power.js).
PLUGS = [
    ("A", "Two flat parallel pins, no earth. North and Central America and Japan. Japanese "
          "plugs have two equal pins, so they fit US sockets; US plugs with one wider pin "
          "may not fit older Japanese sockets."),
    ("B", "Type A plus a round earth pin. It fits Type B sockets only; a two-pin Type A plug "
          "fits a Type B socket."),
    ("C", "The Europlug: two round pins, no earth. Thin enough to fit most round-pin sockets "
          "(Types E, F, J, K, L and N), which makes it the most widely usable plug in the world."),
    ("D", "Three large round pins in a triangle. India, Nepal, Sri Lanka and parts of Africa."),
    ("E", "Two round pins, with the earth pin sticking out of the socket. France, Belgium, "
          "Poland, Czechia, Slovakia. Most plugs sold there are E/F hybrids that fit both."),
    ("F", "Schuko: two round pins with earth clips on the sides. Germany and most of "
          "continental Europe, also South Korea and Russia."),
    ("G", "Three rectangular pins, and a fuse in the plug. The UK, Ireland, Malta, Cyprus, "
          "Singapore, Hong Kong, Malaysia and much of the Gulf."),
    ("H", "Israel's plug. Older sockets take flat pins in a V; newer ones take round pins "
          "and also accept Type C."),
    ("I", "Two flat pins set in a V, often with an earth pin. Australia, New Zealand, "
          "China, Argentina and several Pacific islands."),
    ("J", "Switzerland and Liechtenstein: three round pins. Swiss sockets also take Type C."),
    ("K", "Denmark and Greenland: two round pins and a half-round earth pin. The sockets "
          "also take Type C."),
    ("L", "Italy: three round pins in a row, in a 10 A and a thicker 16 A size. The sockets "
          "also take Type C."),
    ("M", "A larger version of Type D. South Africa, Lesotho, Eswatini, and some sockets "
          "in India and the Gulf."),
    ("N", "Brazil's standard, adopted by South Africa for new sockets: three round pins. "
          "The sockets also take Type C."),
    ("O", "Thailand's national plug (TIS 166-2549), three round pins. The IEC table does "
          "not list it; Thai sockets are usually built to take Type A and C as well."),
]


def e(s: str) -> str:
    return html.escape(s, quote=True)


def types_label(types: list[str]) -> str:
    return ", ".join(types)


def volts_label(volts: list[str]) -> str:
    return " / ".join(f"{v} V" for v in volts)


def hz_label(hz: list[str]) -> str:
    return " / ".join(f"{h} Hz" for h in hz)


def load() -> list[dict]:
    with CSV_PATH.open(encoding="utf-8") as f:
        rows = []
        for r in csv.DictReader(f):
            rows.append({
                "code": r["code"], "name": r["name"],
                "types": r["types"].split(), "volts": r["volts"].split(),
                "hz": r["hz"].split(), "also_reported": r["also_reported"].split(),
                "page": r["page"],
            })
    return rows


def table_rows(rows: list[dict]) -> str:
    out = []
    for r in rows:
        name = e(r["name"])
        if r["page"]:
            name = f'<a href="{r["page"]}.html">{name}</a>'
        note = ""
        if r["also_reported"]:
            note = f'Other sources also list {types_label(r["also_reported"])}'
        out.append(
            f'<tr id="{r["code"].lower()}" data-c="{r["code"]}" data-t="{" ".join(r["types"])}" '
            f'data-v="{" ".join(r["volts"])}" data-h="{" ".join(r["hz"])}">'
            f'<th scope="row">{name}</th><td>{types_label(r["types"])}</td>'
            f'<td>{volts_label(r["volts"])}</td><td>{hz_label(r["hz"])}</td><td>{note}</td></tr>')
    return "\n".join(out)


def options(rows: list[dict], selected: str) -> str:
    return "".join(
        f'<option value="{r["code"]}"{" selected" if r["code"] == selected else ""}>{e(r["name"])}</option>'
        for r in rows)


def page(rows: list[dict]) -> str:
    n = len(rows)
    disputed = sum(1 for r in rows if r["also_reported"])
    title = f"Plugs and Voltage by Country: All {n}, With an Adapter Checker (2026)"
    desc = (f"Plug types, voltage and frequency for {n} countries and territories, from the IEC "
            "listing and cross-checked, with a checker that says whether you need an adapter "
            "or a converter. Free to reuse as CSV or JSON.")
    guides = sorted((r for r in rows if r["page"]), key=lambda r: r["name"])
    guide_links = " · ".join(f'<a href="{r["page"]}.html">{e(r["name"])}</a>' for r in guides)
    plug_list = "\n".join(f'<li id="type-{t.lower()}"><strong>Type {t}.</strong> {e(d)}</li>'
                          for t, d in PLUGS)
    ld = [
        {
            "@context": "https://schema.org", "@type": "Dataset",
            "name": f"Plug types, voltage and frequency by country ({n} countries and territories)",
            "description": desc, "url": URL, "dateModified": CHECKED_ISO,
            "creator": {"@type": "Organization", "name": "Gently Yonder", "url": "https://gentlyyonder.com/"},
            "isBasedOn": [IEC_ARCHIVE, WIKI],
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "isAccessibleForFree": True,
            "distribution": [
                {"@type": "DataDownload", "encodingFormat": "text/csv",
                 "contentUrl": "https://gentlyyonder.com/data/travel-power.csv"},
                {"@type": "DataDownload", "encodingFormat": "application/json",
                 "contentUrl": "https://gentlyyonder.com/data/travel-power.json"},
            ],
        },
        {
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Gently Yonder", "item": "https://gentlyyonder.com/"},
                {"@type": "ListItem", "position": 2, "name": "Plugs and voltage by country"},
            ],
        },
    ]
    ld_html = "\n".join(f'<script type="application/ld+json">\n{json.dumps(b, indent=2, ensure_ascii=False)}\n</script>' for b in ld)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{e(title)} | Gently Yonder</title>
<meta content="{e(desc)}" name="description"/>
<link href="{URL}" rel="canonical"/>
<meta content="index, follow, max-image-preview:large" name="robots"/>
<meta content="website" property="og:type"/>
<meta content="{e(title)}" property="og:title"/>
<meta content="{e(desc)}" property="og:description"/>
<meta content="{URL}" property="og:url"/>
<meta content="Gently Yonder" property="og:site_name"/>
<link href="../style-v2.css" rel="stylesheet"/>
{ld_html}
{ga4_snippet("G-JRGK9CN3B1").rstrip()}
</head>
<body>
<nav aria-label="Breadcrumb" class="breadcrumb">
<ol>
<li><a href="../index.html">Gently Yonder</a></li>
<li aria-current="page">Plugs and voltage by country</li>
</ol>
</nav>
<header class="hero article-hero">
<p class="label">Reference · checked {CHECKED}</p>
<h1>Plugs and voltage by country</h1>
<p class="article-byline">By <a href="../editors.html">Casey</a>, Gently Yonder editor</p>
<p class="subtitle">Plug types, voltage and frequency for {n} countries and territories, and a checker that tells you whether you need an adapter, a converter, or neither.</p>
</header>
<main id="main">
<section class="article">
<aside class="gy-widget">
<p class="gy-widget-h">The quick answer</p>
<p class="gy-widget-blurb">Most phone, laptop and camera chargers say <strong>INPUT 100–240 V</strong>. Those need only a plug adapter, anywhere in this table. A voltage converter matters only for single-voltage appliances, mostly hair dryers and straighteners, when you travel between a 100–127 V country and a 220–240 V one.</p>
</aside>
<h2 id="checker">Do you need an adapter?</h2>
<div class="gy-finder gy-power" id="gy-power">
<form id="gp-form">
<p class="gf-field"><label for="gp-from">Where your plugs are from</label>
<select id="gp-from">{options(rows, "US")}</select></p>
<p class="gf-field"><label for="gp-to">Where you are going</label>
<select id="gp-to">{options(rows, "JP")}</select></p>
</form>
<div aria-live="polite" class="gp-out" id="gp-out"></div>
<noscript><p>The checker needs JavaScript. The table below has the same answer: compare the plug types and voltage of the two countries.</p></noscript>
</div>
<p>The checker counts a plug as fitting only where the socket is built for it: a Type A plug fits a Type B socket, and a two-pin Type C plug fits Type E, F, J, K, L and N sockets. Hotels vary, and some keep universal sockets or spare adapters at reception, but do not count on it.</p>
<h2 id="table">All {n} countries and territories</h2>
<p class="gp-find"><label for="gp-filter">Find a country</label>
<input autocomplete="off" id="gp-filter" placeholder="A country, or a plug such as “type G”" type="search"/></p>
<div class="table-scroll">
<table id="gp-table">
<thead><tr><th scope="col">Country or territory</th><th scope="col">Plug types</th><th scope="col">Voltage</th><th scope="col">Frequency</th><th scope="col">Note</th></tr></thead>
<tbody>
{table_rows(rows)}
</tbody>
</table>
</div>
<p>Linked names have a fuller guide: what to pack, and the questions travellers ask about that country.</p>
<h2 id="adapter-or-converter">Adapter or converter?</h2>
<p>A <strong>plug adapter</strong> changes only the shape, so your plug fits the socket. A <strong>voltage converter</strong> changes the electricity. Look at the small print on each charger: <em>100–240 V</em> means it works on any mains supply in this table and needs only an adapter. A single number, such as <em>120 V</em> or <em>230 V</em>, means it is built for one supply.</p>
<p>Plugging a 120 V-only appliance into a 230 V socket can destroy it within seconds. The other way round, a 230 V appliance on 100–127 V usually runs weakly or not at all. 220 V and 230 V, or 110 V and 120 V, count as the same supply for travel purposes.</p>
<p>Frequency (50 or 60 Hz) rarely matters for chargers. It can make motors run slightly faster or slower and older plug-in clocks gain or lose time.</p>
<h2 id="plug-types">Plug types A to O</h2>
<ul class="gp-types">
{plug_list}
</ul>
<h2 id="sources">Where this data comes from</h2>
<p>Plug types, voltage and frequency come from the World Plugs listing of the <strong>International Electrotechnical Commission (IEC)</strong>, the body that publishes the international plug and socket standards. The IEC retired that guide in 2026 and now points travellers to adapter makers and travel websites. We read the version saved by the Internet Archive on <a href="{IEC_ARCHIVE}" rel="noopener">19 January 2026</a>, which matches the November 2025 copy country for country.</p>
<p>We checked every row against Wikipedia’s <a href="{WIKI}" rel="noopener">Mains electricity by country</a>. In {disputed} rows it lists plug types that the IEC does not; the Note column says which. Where the two disagree, expect the IEC types in hotels and carry a universal adapter. The IEC lists some voltages at 220 V that are now nominally 230 V, and the reverse; for travel the difference does not matter.</p>
<p>Country names follow current usage (Eswatini, North Macedonia, Türkiye). If you spot an error, tell us and we will log the fix on our <a href="../corrections.html">corrections page</a>. Read <a href="../methodology.html">how we verify</a>.</p>
<h2 id="reuse">Use this data</h2>
<p>The whole table is free to reuse under <a href="https://creativecommons.org/licenses/by/4.0/" rel="noopener">CC BY 4.0</a>: download <a href="../data/travel-power.csv">CSV</a> or <a href="../data/travel-power.json">JSON</a>. Please link to this page, for example:</p>
<p class="gp-cite"><code>Source: &lt;a href="{URL}"&gt;Plugs and voltage by country, Gently Yonder&lt;/a&gt; (IEC data, checked {CHECKED})</code></p>
<h2 id="country-guides">Country guides</h2>
<p>{guide_links}</p>
<h2 id="related">Related</h2>
<ul>
<li><a href="../articles/best-travel-adapter-asia-2026.html">The best travel adapter for Asia (2026)</a></li>
<li><a href="../articles/best-power-bank-travel-2026.html">The best power bank for travel (2026)</a>, and the airline rules for carrying one</li>
<li><a href="../checklist-generator.html">Checklist generator</a>: a packing list for your trip</li>
</ul>
</section>
</main>
<footer></footer>
<script defer src="../js/gy-power.js"></script>
</body>
</html>
"""


def main() -> None:
    rows = load()
    site, docs = REPO / "site", REPO / "docs"
    out = {
        "travel-power/index.html": page(rows),
        "data/travel-power.json": json.dumps({
            "source": "IEC World Plugs (archived 19 January 2026), cross-checked with Wikipedia",
            "checked": CHECKED_ISO, "license": "CC BY 4.0", "url": URL,
            "countries": [{k: r[k] for k in ("code", "name", "types", "volts", "hz", "also_reported")} for r in rows],
        }, ensure_ascii=False, indent=1) + "\n",
    }
    for rel, text in out.items():
        (site / rel).write_text(text, encoding="utf-8")
    with (site / "data/travel-power.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iso_code", "country", "plug_types", "voltage_v", "frequency_hz", "also_reported_types"])
        for r in rows:
            w.writerow([r["code"], r["name"], " ".join(r["types"]), " ".join(r["volts"]),
                        " ".join(r["hz"]), " ".join(r["also_reported"])])
    for rel in [*out, "data/travel-power.csv", "js/gy-power.js"]:
        shutil.copyfile(site / rel, docs / rel)
    print(f"travel-power hub: {len(rows)} countries, "
          f"{sum(1 for r in rows if r['also_reported'])} with other sources noted")


if __name__ == "__main__":
    main()
