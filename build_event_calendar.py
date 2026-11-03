"""Build stay/events.html: every event and season guide on one calendar, soonest first.

Rows come from data/event_calendar.json (each date is one its guide states); a row drops off the day
after its end date. Each row links the guide and, as the partner action, the Stay22 hotel map around
the area that guide recommends (stay22.PAGES), so a reader who already knows the date can go
straight to rooms. Writes site/ and docs/.

usage: .venv/bin/python build_event_calendar.py
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

import stay22
from add_footer import block as _footer_block
from add_ga4 import snippet as _ga4_snippet
from add_global_nav import block as _nav_block
from add_social_meta import apply_text as apply_social

REPO = Path(__file__).resolve().parent
REL = "stay/events.html"
URL = f"https://gentlyyonder.com/{REL}"
TITLE = "Where to Stay for Events 2026/27: A Calendar of Dates That Fill Hotels | Gently Yonder"
H1 = "Events that fill hotels: a calendar"
DESC = ("Christmas markets, New Year's Eve, carnivals, festivals, races and blossom seasons from November "
        "2026 to spring 2027, with dates, where to stay and hotels near each one.")
INTRO = ("These are the dates when hotels near the action sell out first. Each line gives the date its "
         "guide confirms, the guide that matches areas and named hotels to the event, and a map of rooms "
         "around the area we recommend. Dates marked “usually” are typical seasons, not fixed dates.")
NOTE = ("Dates come from each organiser or official source, as stated in the guide, and drop off this page "
        "when the event ends. Hotel maps are from our partner Stay22: if you book through them we may earn "
        "a commission, at no extra cost to you.")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def _rates(slug: str) -> tuple[str, str]:
    p = stay22.PAGES[slug]
    return stay22.area_rates(p["lat"], p["lng"]), p["area"]


def _row(e: dict, kind: str) -> str:
    href, area = _rates(e["slug"])
    when = html.escape(e["when"])
    if e.get("usual"):
        when = f"<span class=\"gy-cal-usual\">Usually:</span> {when.removeprefix('usually ')}"
    place = f'<span class="gy-cal-place">{html.escape(e["place"])}</span>' if e.get("place") else ""
    return (f'<li class="gy-cal-row gy-cal-{kind}">'
            f'<p class="gy-cal-when">{when}</p>'
            f'<p class="gy-cal-name"><a href="../articles/{e["slug"]}.html">{html.escape(e["name"])}</a>{place}</p>'
            f'<p class="gy-cal-actions"><a class="gy-cal-guide" href="../articles/{e["slug"]}.html">Where to stay</a>'
            f'<a class="gy-cal-rates" href="{html.escape(href)}" rel="nofollow sponsored noopener" target="_blank" '
            f'data-placement="event_calendar">Hotels around {html.escape(area)}</a></p></li>')


def render(today: date) -> str:
    data = json.loads((REPO / "data" / "event_calendar.json").read_text(encoding="utf-8"))
    iso = today.isoformat()
    events = sorted((e for e in data["events"] if e["end"] >= iso), key=lambda e: (e["start"], e["end"]))
    months: dict[str, list[dict]] = {}
    for e in events:
        y, m = (int(x) for x in max(e["start"], iso)[:7].split("-"))
        months.setdefault(f"{MONTHS[m - 1]} {y}", []).append(e)
    sections = []
    for label, items in months.items():
        anchor = label.lower().replace(" ", "-")
        sections.append(f'<section class="gy-cal-month" id="{anchor}">\n<h2>{label}</h2>\n<ul class="gy-cal-list">\n'
                        + "\n".join(_row(e, "event") for e in items) + "\n</ul>\n</section>")
    seasons = [s for s in data["seasons"] if s["end"] >= iso]
    if seasons:
        sections.append('<section class="gy-cal-month" id="seasons">\n<h2>Seasons: snow, northern lights and leaves</h2>\n'
                        '<ul class="gy-cal-list">\n' + "\n".join(_row(s, "season") for s in seasons) + "\n</ul>\n</section>")
    jump = " · ".join(f'<a href="#{k.lower().replace(" ", "-")}">{k}</a>' for k in months)
    if seasons:
        jump += ' · <a href="#seasons">Seasons</a>'
    items = [f"https://gentlyyonder.com/articles/{e['slug']}.html" for e in events + seasons]
    ld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "url": URL,
                     "name": H1, "description": DESC,
                     "isPartOf": {"@type": "WebSite", "name": "Gently Yonder", "url": "https://gentlyyonder.com/"},
                     "mainEntity": {"@type": "ItemList", "numberOfItems": len(dict.fromkeys(items)),
                                    "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": u}
                                                        for i, u in enumerate(dict.fromkeys(items))]}},
                    ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{TITLE}</title>
<meta name="description" content="{html.escape(DESC)}" />
<link rel="canonical" href="{URL}" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<link rel="stylesheet" href="../style-v2.css" />
<script type="application/ld+json">{ld}</script>
{_ga4_snippet("G-JRGK9CN3B1").strip()}
</head>
<body>
{_nav_block("../")}
<nav class="breadcrumb" aria-label="Breadcrumb">
<ol><li><a href="../index.html">Gently Yonder</a></li><li><a href="index.html">Stay</a></li><li aria-current="page">Event calendar</li></ol>
</nav>
<header class="gy-arch-head">
<div class="gy-arch-head-inner">
<p class="label">Stay</p>
<h1>{H1}</h1>
<p>{INTRO}</p>
<p class="gy-cal-jump">{jump}</p>
</div>
</header>
<main class="gy-archive gy-cal" id="main">
<aside class="gy-hub-note"><p>{NOTE}</p></aside>
{chr(10).join(sections)}
<p class="back-link"><a href="index.html">&larr; All stay guides</a></p>
</main>
{_footer_block("../")}
<script defer src="../js/gy-reveal.js"></script>
<script src="../js/email-popup.js" data-root="../" defer></script>
</body>
</html>
"""


def main() -> None:
    page = apply_social(render(date.today()))
    for base in ("site", "docs"):
        out = REPO / base / REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
    print(f"  event calendar written: {REL}")


if __name__ == "__main__":
    main()
