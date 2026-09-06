#!/usr/bin/env python3
"""
build_gear_page.py — generate a standalone, filterable, image-rich Travel Gear
Directory at site/gear.html (mirrored to docs/gear.html) from products.csv.

Why a dedicated page: the homepage plain-text list looked flat. This page groups
gear by category with header images, a filter/sort bar, and clean product cards.

Compliance note (Amazon Associates Operating Agreement): live product prices and
product photos may only be shown via the Product Advertising API or approved
tools, and hardcoded/stale prices are prohibited. This site is not PA-API
qualified, so cards use representative category images (our own) and a
"Check price on Amazon" CTA — the price lives on Amazon. If/when PA-API is
available, wire live price + image in the render_card() function.

Usage:
  python build_gear_page.py            # writes site/ + docs/ gear.html
"""
from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent
CSV = REPO / "site" / "products.csv"
GA4 = "G-JRGK9CN3B1"

# category -> (header image in images/pinterest/, one-line blurb)
CATEGORY_META: dict[str, tuple[str, str]] = {
    "eSIM & Connectivity": ("esim-photo.webp", "Stay online from the moment you land — eSIMs, hotspots, and the small stuff."),
    "Packing Essentials": ("capsule-photo.webp", "The organisers and cubes that make a carry-on repack take five minutes."),
    "Flight Comfort": ("carry-on-photo.webp", "Sleep, hydrate, and land a little less wrecked."),
    "Power & Charging": ("travel-edc-photo.webp", "Keep every device alive across time zones and long transit days."),
    "Travel Safety": ("airport-security-checklist-photo.webp", "Track your bags, protect your documents, and travel with quiet confidence."),
    "Camera Travel Gear": ("travel-edc-photo-w2.webp", "Carry and protect a camera kit without the bulk."),
    "Sun & Beach": ("beach-photo.webp", "Reef-safe sun care and the light, quick-dry pieces for hot places."),
    "Hotel Stay Comfort": ("hotels-photo.webp", "Small comforts that make a hotel room feel a little more like yours."),
    "Travel Health & Insurance": ("insurance-photo.webp", "Cover, first-aid, and the health basics worth sorting before you go."),
}
DEFAULT_IMG = "carry-on-photo.webp"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-").replace("--", "-")


def read_products() -> dict[str, list[dict]]:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    with open(CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_cat[row["category"]].append(row)
    return by_cat


def cta_for(row: dict) -> str:
    mon = (row.get("monetization") or "").lower()
    if mon == "amazon":
        return "Check price on Amazon &rarr;"
    url = row.get("url", "")
    if "airalo" in url:
        return "Browse Airalo plans &rarr;"
    if "ekta" in url:
        return "Get an insurance quote &rarr;"
    return "View &rarr;"


def render_card(row: dict) -> str:
    name = esc(row["item"])
    desc = esc(row["description"])
    url = esc(row["url"])
    pri = esc(row.get("priority", "3"))
    intent = esc(row.get("buyer_intent", ""))
    return (
        f'<article class="gear-card" data-name="{name}" data-priority="{pri}" data-intent="{intent}">\n'
        f'  <h3 class="gear-card-name">{name}</h3>\n'
        f'  <p class="gear-card-desc">{desc}</p>\n'
        f'  <a class="gear-card-cta" href="{url}" rel="nofollow sponsored noopener" target="_blank">{cta_for(row)}</a>\n'
        f'</article>'
    )


def render_section(cat: str, rows: list[dict]) -> str:
    img, blurb = CATEGORY_META.get(cat, (DEFAULT_IMG, ""))
    sid = slugify(cat)
    cards = "\n".join(render_card(r) for r in rows)
    return (
        f'<section class="gear-cat" id="{sid}" data-category="{esc(cat)}">\n'
        f'  <div class="gear-cat-head" style="background-image:linear-gradient(rgba(23,32,51,.55),rgba(23,32,51,.75)),url(images/pinterest/{img})">\n'
        f'    <h2>{esc(cat)}</h2>\n'
        f'    <p>{esc(blurb)}</p>\n'
        f'  </div>\n'
        f'  <div class="gear-grid">\n{cards}\n  </div>\n'
        f'</section>'
    )


NAV = ('<nav class="gy-topnav" aria-label="Primary"><div class="gy-topnav-inner">'
       '<a class="gy-topnav-brand" href="index.html">Gently Yonder</a>'
       '<div class="gy-topnav-links"><a href="index.html#guides">Guides</a>'
       '<a href="index.html#profiles">Destinations</a>'
       '<a href="articles/esim-activation-and-preparation.html">eSIM &amp; Tech</a>'
       '<a href="articles/travel-insurance-compared.html">Insurance</a>'
       '<a href="tools/esim-finder.html">Tools</a>'
       '<a href="gear.html">Gear</a>'
       '<a href="about.html">About</a></div></div></nav>')

GA4_BLOCK = f"""<!-- BEGIN GA4 (managed by add_ga4.py) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA4}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  var gyCfg = {{ anonymize_ip: true }};
  try {{
    if (location.hash === '#gy-internal') localStorage.setItem('gy_internal', '1');
    if (location.hash === '#gy-public') localStorage.removeItem('gy_internal');
    if (localStorage.getItem('gy_internal') === '1') gyCfg.traffic_type = 'internal';
  }} catch (e) {{}}
  gtag('config', '{GA4}', gyCfg);
</script>
<!-- END GA4 -->"""

CSS = """
.gear-intro{max-width:1100px;margin:0 auto;padding:0 clamp(20px,4vw,40px)}
.gear-disclosure{font-size:.86rem;color:#647084;max-width:70ch;margin:14px auto 0}
.gear-controls{position:sticky;top:0;z-index:20;background:var(--surface,#F8F4E9);border-top:1px solid rgba(23,32,51,.08);border-bottom:1px solid rgba(23,32,51,.08);margin-top:22px}
.gear-controls-inner{max-width:1100px;margin:0 auto;padding:12px clamp(20px,4vw,40px);display:flex;flex-wrap:wrap;gap:10px 8px;align-items:center}
.gear-filter{font:inherit;font-size:.86rem;padding:7px 14px;border:1px solid rgba(23,32,51,.18);border-radius:999px;background:rgba(255,255,255,.6);color:var(--navy,#172033);cursor:pointer;transition:border-color .15s,background .15s}
.gear-filter:hover{border-color:#B8945F}
.gear-filter[aria-pressed="true"]{background:var(--navy,#172033);color:#F8F4E9;border-color:var(--navy,#172033)}
.gear-sort{margin-left:auto;font:inherit;font-size:.86rem;padding:7px 12px;border:1px solid rgba(23,32,51,.18);border-radius:8px;background:#fff;color:var(--navy,#172033)}
.gear-cat{max-width:1100px;margin:34px auto 0;padding:0 clamp(20px,4vw,40px)}
.gear-cat-head{border-radius:14px;padding:34px 28px;background-size:cover;background-position:center;color:#F8F4E9;margin-bottom:20px}
.gear-cat-head h2{margin:0 0 6px;font-size:clamp(1.5rem,3vw,2rem);color:#fff}
.gear-cat-head p{margin:0;font-size:.98rem;color:rgba(248,244,233,.9);max-width:56ch}
.gear-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.gear-card{display:flex;flex-direction:column;border:1px solid rgba(23,32,51,.12);border-radius:12px;padding:18px 18px 16px;background:#fff;transition:box-shadow .15s,transform .15s}
.gear-card:hover{box-shadow:0 10px 26px rgba(23,32,51,.10);transform:translateY(-2px)}
.gear-card-name{margin:0 0 8px;font-size:1.05rem;line-height:1.3;color:var(--navy,#172033)}
.gear-card-desc{margin:0 0 16px;font-size:.9rem;line-height:1.5;color:#4a5163;flex:1}
.gear-card-cta{align-self:flex-start;font-size:.9rem;font-weight:700;padding:9px 15px;border-radius:999px;background:#C9A84C;color:#172033;text-decoration:none;transition:background .15s}
.gear-card-cta:hover{background:#d8ba61}
.gear-price-note{font-size:.78rem;color:#8a94ab;margin-top:8px}
.gear-empty{max-width:1100px;margin:30px auto;padding:0 clamp(20px,4vw,40px);color:#647084}
@media (max-width:560px){.gear-sort{margin-left:0}}
"""

JS = """
(function(){
  var filters=document.querySelectorAll('.gear-filter');
  var sort=document.getElementById('gear-sort');
  var cats=document.querySelectorAll('.gear-cat');
  function applyFilter(cat){
    filters.forEach(function(b){b.setAttribute('aria-pressed', b.dataset.cat===cat?'true':'false');});
    cats.forEach(function(s){ s.hidden = !(cat==='all' || s.dataset.category===cat); });
  }
  function applySort(mode){
    cats.forEach(function(s){
      var grid=s.querySelector('.gear-grid');
      var cards=Array.prototype.slice.call(grid.querySelectorAll('.gear-card'));
      cards.sort(function(a,b){
        if(mode==='az') return a.dataset.name.localeCompare(b.dataset.name);
        return (a.dataset.priority||'9').localeCompare(b.dataset.priority||'9'); // featured: priority asc
      });
      cards.forEach(function(c){grid.appendChild(c);});
    });
  }
  filters.forEach(function(b){b.addEventListener('click',function(){applyFilter(b.dataset.cat);});});
  if(sort) sort.addEventListener('change',function(){applySort(sort.value);});
  applySort('featured');
})();
"""


def build_page(by_cat: dict[str, list[dict]]) -> str:
    cats = list(CATEGORY_META.keys()) + [c for c in by_cat if c not in CATEGORY_META]
    cats = [c for c in cats if c in by_cat]
    pills = '<button class="gear-filter" data-cat="all" aria-pressed="true">All</button>\n' + "\n".join(
        f'<button class="gear-filter" data-cat="{esc(c)}" aria-pressed="false">{esc(c)}</button>' for c in cats
    )
    sections = "\n".join(render_section(c, by_cat[c]) for c in cats)
    total = sum(len(v) for v in by_cat.values())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Travel Gear Directory: Sorted Picks by Category | Gently Yonder</title>
<meta name="description" content="A sorted, filterable travel gear directory — eSIMs, packing, power, safety, flight comfort, and more, grouped by category with our honest picks. Check current prices on Amazon." />
<link rel="canonical" href="https://gentlyyonder.com/gear.html" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta property="og:type" content="website" />
<meta property="og:title" content="Travel Gear Directory | Gently Yonder" />
<meta property="og:description" content="A sorted, filterable travel gear directory grouped by category, with our honest picks." />
<meta property="og:url" content="https://gentlyyonder.com/gear.html" />
<meta property="og:site_name" content="Gently Yonder" />
<link rel="stylesheet" href="style-v2.css" />
{GA4_BLOCK}
<!-- BEGIN favicon (managed by add_favicon.py) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml"/>
<link rel="icon" href="/favicon-48.png" type="image/png" sizes="48x48"/>
<link rel="icon" href="/favicon-192.png" type="image/png" sizes="192x192"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<!-- END favicon -->
<style>{CSS}</style>
</head>
<body>
{NAV}
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol><li><a href="index.html">Gently Yonder</a></li><li aria-current="page">Gear directory</li></ol>
</nav>
<header class="gy-arch-head">
<div class="gy-arch-head-inner">
<p class="label">The directory</p>
<h1>Travel gear directory</h1>
<p>Our honest gear picks, grouped by category and sortable — {total} items across {len(cats)} categories. Filter to what you need, then check the current price on Amazon.</p>
</div>
</header>
<main>
<div class="gear-intro">
<p class="gear-disclosure">Disclosure: some links are affiliate links. As an Amazon Associate, Gently Yonder may earn from qualifying purchases at no extra cost to you. Prices and availability are shown on the retailer's site, not here — always confirm the current price before buying.</p>
</div>
<div class="gear-controls">
<div class="gear-controls-inner">
{pills}
<select class="gear-sort" id="gear-sort" aria-label="Sort products">
<option value="featured">Sort: Featured</option>
<option value="az">Sort: A &ndash; Z</option>
</select>
</div>
</div>
{sections}
</main>
<footer>
  <p>Gently Yonder is an independent travel editorial project.
    <a href="about.html">About</a> · <a href="methodology.html">Methodology</a> ·
    <a href="editors.html">Editors</a> · <a href="privacy.html">Privacy</a> ·
    <a href="https://x.com/TripWorldAdvice">@TripWorldAdvice</a></p>
</footer>
<script defer src="js/gy-reveal.js"></script>
<script src="js/email-popup.js" data-root="" defer></script>
<script>{JS}</script>
</body>
</html>
"""


def main() -> None:
    by_cat = read_products()
    page = build_page(by_cat)
    for base in ("site", "docs"):
        (REPO / base / "gear.html").write_text(page, encoding="utf-8")
    print(f"Built site/gear.html and docs/gear.html ({sum(len(v) for v in by_cat.values())} products, {len(by_cat)} categories)")


if __name__ == "__main__":
    main()
