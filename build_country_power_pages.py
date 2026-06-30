#!/usr/bin/env python3
"""
build_country_power_pages.py

Programmatic-SEO generator for "Power adapter & plug by country" pages.
This targets high-volume, commercial-intent queries ("what plug does
Japan use", "travel adapter for Italy") that don't overlap our editorial
country profiles, and ties naturally to an Amazon universal-adapter
affiliate link (tag=packlightpick-20).

Design choices that keep this honest (not a thin-content farm):
  * Data is verifiable reference fact (IEC plug types, mains voltage),
    seeded in programmatic/plugs.csv — not fabricated per-page prose.
  * Each page is genuinely useful: at-a-glance table, who-needs-an-adapter
    guidance, a voltage caveat, a country-specific quirk, FAQ, and links
    into our deeper guides.
  * To scale, add verified rows to plugs.csv and re-run. We do not
    auto-generate countries we can't vouch for.

Outputs:
  site/travel-power/index.html        hub, grouped by region
  site/travel-power/<slug>.html       one page per country
  (mirrored to docs/, added to sitemap.xml)

Usage:
  python build_country_power_pages.py            # dry run (counts only)
  python build_country_power_pages.py --write
"""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import OrderedDict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent
CSV_PATH = REPO / "programmatic" / "plugs.csv"
BASE_URL = "https://gentlyyonder.com"
GA4_ID = "G-JRGK9CN3B1"

# Country profiles we already publish — link to them when relevant.
PROFILE_LINKS = {
    "japan": "../countries/japan/index.html",
    "vietnam": "../countries/vietnam/index.html",
    "australia": "../countries/australia/index.html",
    "south-korea": "../articles/south-korea-country-profile.html",
}

GA4 = f"""  <!-- BEGIN GA4 (managed by add_ga4.py) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_ID}', {{ anonymize_ip: true }});
</script>
<!-- END GA4 -->"""

DRIVE = """  <!-- BEGIN Travelpayouts Drive (managed by add_travelpayouts_drive.py) -->
  <script nowprocket data-noptimize="1" data-cfasync="false" data-wpfc-render="false" seraph-accel-crit="1" data-no-defer="1">
    (function () {
      var script = document.createElement("script");
      script.async = 1;
      script.src = 'https://tpembars.com/NTQzNzE5.js?t=543719';
      document.head.appendChild(script);
    })();
  </script>
  <!-- END Travelpayouts Drive -->"""

FOOT_SCRIPTS = """  <script async src="https://tally.so/widgets/embed.js"></script>
  <!-- BEGIN Pinterest hover-Save SDK -->
  <script async defer src="https://assets.pinterest.com/js/pinit.js" data-pin-hover="true"></script>
  <!-- END Pinterest hover-Save SDK -->"""


def e(s: str) -> str:
    return html.escape(s, quote=True)


def amazon_link(country: str) -> str:
    q = ("+".join(country.lower().split()) + "+travel+plug+adapter+usb+c")
    return f"https://www.amazon.com/s?k={q}&tag=packlightpick-20"


def country_page(row: dict) -> str:
    slug = row["slug"]
    country = row["country"]
    plug = row["plug_types"]
    volt = row["voltage"]
    freq = row["frequency"]
    notes = row["traveler_notes"]
    quirk = row["quirk"]
    url = f"{BASE_URL}/travel-power/{slug}.html"
    title = f"Power Adapter for {country}: Plugs, Voltage & What to Pack (2026)"
    desc = (f"What plug and voltage {country} uses (Type {plug}, {volt}), whether you "
            f"need a travel adapter or voltage converter, and what to pack.")
    amazon = amazon_link(country)

    faq = [
        (f"What plug type does {country} use?",
         f"{country} uses Type {plug} plugs at {volt}, {freq}. If your devices use a "
         f"different plug type, you will need a travel plug adapter."),
        (f"Do I need a voltage converter for {country}?",
         f"{country} runs at {volt}. Most modern phones, laptops and camera chargers are "
         f"dual-voltage (rated 100–240 V) and need only a plug adapter, not a converter. "
         f"Check the small print on your charger — if it says 100–240 V, you are fine. "
         f"Single-voltage items such as some hair tools may need a converter."),
        (f"Will my phone charger work in {country}?",
         f"Almost certainly, with the right plug adapter. Phone and laptop chargers are "
         f"nearly always dual-voltage, so they handle {country}'s {volt} supply; you just "
         f"need an adapter that fits a Type {plug} socket."),
    ]
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq
        ],
    }
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "url": url,
        "datePublished": date.today().isoformat(),
        "dateModified": date.today().isoformat(),
        "author": {"@type": "Organization", "name": "Travel Now", "url": BASE_URL + "/"},
        "publisher": {"@type": "Organization", "name": "Travel Now", "url": BASE_URL + "/"},
        "mainEntityOfPage": url,
        "inLanguage": "en",
    }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Travel Now", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Travel Power",
             "item": BASE_URL + "/travel-power/"},
            {"@type": "ListItem", "position": 3, "name": f"{country} adapter"},
        ],
    }

    faq_html = "\n".join(
        f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq
    )

    profile_li = ""
    if slug in PROFILE_LINKS:
        profile_li = (f'<li><a href="{PROFILE_LINKS[slug]}">{e(country)} country profile</a> '
                      f'— history, society, and deeper travel preparation.</li>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)} | Travel Now</title>
<meta name="description" content="{e(desc)}" />
<link rel="canonical" href="{url}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(desc)}" />
<meta property="og:url" content="{url}" />
<meta property="og:site_name" content="Travel Now" />
<link rel="stylesheet" href="../style-v2.css" />
<script type="application/ld+json">
{json.dumps(article_schema, indent=2)}
</script>
<script type="application/ld+json">
{json.dumps(faq_schema, indent=2)}
</script>
<script type="application/ld+json">
{json.dumps(breadcrumb_schema, indent=2)}
</script>
{GA4}
{DRIVE}
</head>
<body>
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol>
<li><a href="../index.html">Travel Now</a></li>
<li><a href="index.html">Travel Power</a></li>
<li aria-current="page">{e(country)}</li>
</ol>
</nav>
<header class="hero article-hero">
<p class="label">Travel Power</p>
<h1>Power Adapter for {e(country)}</h1>
<p class="subtitle">What plug and voltage {e(country)} uses, whether you need an adapter or
a converter, and exactly what to pack.</p>
</header>
<main>
<section class="article">
<p class="article-lede">
{e(country)} uses <strong>Type {e(plug)}</strong> plugs at <strong>{e(volt)}</strong> ({e(freq)}).
Here is what that means for your chargers, and the one thing to check before you buy an adapter.
</p>

<h2>{e(country)} at a glance</h2>
<table class="prep-table">
<tbody>
<tr><th>Plug type(s)</th><td>Type {e(plug)}</td></tr>
<tr><th>Voltage</th><td>{e(volt)}</td></tr>
<tr><th>Frequency</th><td>{e(freq)}</td></tr>
</tbody>
</table>

<h2>Do you need an adapter?</h2>
<p>{e(notes)}</p>
<p>{e(quirk)}</p>

<h2>Adapter vs voltage converter — the part people get wrong</h2>
<p>
A <strong>plug adapter</strong> only changes the shape of the pins so your plug fits the
socket. A <strong>voltage converter</strong> changes the electricity itself. The good news:
most travel electronics — phones, laptops, tablets, camera and most modern chargers — are
<strong>dual-voltage</strong>, rated <em>100–240 V</em>. For those you need only a plug
adapter, even in {e(country)}. Look for "INPUT: 100–240V" printed on the charger. Single-voltage
appliances (some hair dryers, straighteners, small kettles) are the ones that may need a
converter — or are better bought locally.
</p>

<div class="product-grid article-products">
<article class="product-card">
<h4>Universal travel adapter (USB-C)</h4>
<p>A single universal adapter with USB-C Power Delivery covers {e(country)} and most other
destinations, and charges a phone and laptop from one socket. The most useful sub-$40 item
for international travel.</p>
<a class="product-link" href="{amazon}" rel="nofollow sponsored noopener" target="_blank">Browse universal adapters on Amazon</a>
</article>
</div>

<h2>Before you fly</h2>
<ul>
<li>Pack one universal adapter rather than several country-specific ones.</li>
<li>Confirm each charger says 100–240 V — if so, no converter needed.</li>
<li>Bring a small power strip to turn one adapter into several outlets.</li>
</ul>

<h2>FAQ: power and plugs in {e(country)}</h2>
<div class="faq">
{faq_html}
</div>

<div class="tip-box">
<strong>Travel Now tip:</strong> Reference data like plug types and voltage is stable, but
hotels and new builds vary. If a socket doesn't match, hotel reception almost always keeps
spare adapters at the desk.
</div>

<section class="related-articles">
<h2>Keep reading on Travel Now</h2>
<ul>
<li><a href="../articles/everyday-carry-essentials-for-travel.html">Travel EDC Checklist</a> — the power bank, cables, and adapter that ride in your day bag.</li>
<li><a href="../articles/esim-activation-and-preparation.html">eSIM Setup for International Travel</a> — land with data already working.</li>
<li><a href="index.html">All travel-power guides</a> — plugs and voltage for more countries.</li>
{profile_li}
</ul>
</section>

<p style="font-size:0.86rem;color:#647084;">
Disclosure: this page contains affiliate links. As an Amazon Associate, Travel Now may earn
from qualifying purchases at no extra cost to you. Plug and voltage data is provided as
general preparation guidance — always check your device labels and confirm locally.
</p>
</section>
</main>
<footer>
<p>
Travel Now is an independent travel editorial project.
<a href="../about.html">About</a> · <a href="../methodology.html">Methodology</a> ·
<a href="../privacy.html">Privacy</a> ·
<a href="https://x.com/TripWorldAdvice">@TripWorldAdvice</a>
</p>
</footer>
{FOOT_SCRIPTS}
</body>
</html>
"""


def index_page(rows: list[dict]) -> str:
    url = f"{BASE_URL}/travel-power/"
    by_region: OrderedDict[str, list[dict]] = OrderedDict()
    for r in rows:
        by_region.setdefault(r["region"], []).append(r)

    sections = []
    for region, items in by_region.items():
        lis = "\n".join(
            f'<li><a href="{r["slug"]}.html">{e(r["country"])}</a> '
            f'— Type {e(r["plug_types"])}, {e(r["voltage"])}</li>'
            for r in sorted(items, key=lambda x: x["country"])
        )
        sections.append(f"<h2>{e(region)}</h2>\n<ul>\n{lis}\n</ul>")
    body = "\n".join(sections)

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Travel Now", "item": BASE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Travel Power"},
        ],
    }
    title = "Travel Power Adapters by Country: Plugs & Voltage Guide (2026)"
    desc = ("A country-by-country guide to travel plugs and voltage — which adapter you need, "
            "whether you need a voltage converter, and what to pack.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)} | Travel Now</title>
<meta name="description" content="{e(desc)}" />
<link rel="canonical" href="{url}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta property="og:type" content="website" />
<meta property="og:title" content="{e(title)}" />
<meta property="og:description" content="{e(desc)}" />
<meta property="og:url" content="{url}" />
<meta property="og:site_name" content="Travel Now" />
<link rel="stylesheet" href="../style-v2.css" />
<script type="application/ld+json">
{json.dumps(breadcrumb_schema, indent=2)}
</script>
{GA4}
{DRIVE}
</head>
<body>
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol>
<li><a href="../index.html">Travel Now</a></li>
<li aria-current="page">Travel Power</li>
</ol>
</nav>
<header class="hero article-hero">
<p class="label">Travel Power</p>
<h1>Travel Power Adapters by Country</h1>
<p class="subtitle">Which plug and voltage each destination uses, whether you need an adapter
or a converter, and what to pack. Pick a country to get the details.</p>
</header>
<main>
<section class="article">
<p class="article-lede">
Most travel electronics are dual-voltage, so for the majority of trips you need only the right
<em>plug adapter</em> — not a heavy voltage converter. These guides tell you exactly which is
which, country by country.
</p>
{body}
<div class="tip-box">
<strong>Travel Now tip:</strong> One good universal adapter with USB-C covers almost everywhere
in this list. See any country page for a current pick.
</div>
<section class="related-articles">
<h2>Related</h2>
<ul>
<li><a href="../articles/everyday-carry-essentials-for-travel.html">Travel EDC Checklist</a> — what rides in your day bag.</li>
<li><a href="../articles/esim-activation-and-preparation.html">eSIM Setup for International Travel</a> — connectivity before you land.</li>
</ul>
</section>
</section>
</main>
<footer>
<p>
Travel Now is an independent travel editorial project.
<a href="../about.html">About</a> · <a href="../methodology.html">Methodology</a> ·
<a href="../privacy.html">Privacy</a> ·
<a href="https://x.com/TripWorldAdvice">@TripWorldAdvice</a>
</p>
</footer>
{FOOT_SCRIPTS}
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write files (otherwise dry run)")
    args = ap.parse_args()

    with CSV_PATH.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    site_dir = REPO / "site" / "travel-power"
    docs_dir = REPO / "docs" / "travel-power"
    pages = {f"{r['slug']}.html": country_page(r) for r in rows}
    pages["index.html"] = index_page(rows)

    if args.write:
        site_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)
        for name, content in pages.items():
            (site_dir / name).write_text(content, encoding="utf-8")
            (docs_dir / name).write_text(content, encoding="utf-8")
        # sitemap
        add_to_sitemap([f"{BASE_URL}/travel-power/"] +
                       [f"{BASE_URL}/travel-power/{r['slug']}.html" for r in rows])

    print(f"  countries     : {len(rows)}")
    print(f"  pages         : {len(pages)} (incl. hub index)")
    print(f"  {'wrote to site/ + docs/travel-power/' if args.write else '(dry run — pass --write)'}")


def add_to_sitemap(urls: list[str]) -> None:
    for p in [REPO / "site" / "sitemap.xml", REPO / "docs" / "sitemap.xml"]:
        s = p.read_text(encoding="utf-8")
        block = ""
        for u in urls:
            if u in s:
                continue
            block += (f"  <url>\n    <loc>{u}</loc>\n"
                      f"    <changefreq>yearly</changefreq>\n    <priority>0.6</priority>\n  </url>\n")
        if block:
            s = s.replace("</urlset>", block + "</urlset>")
            p.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
