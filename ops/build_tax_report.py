"""Build the public "Tourist taxes around the world 2026" data report from data/tourist_taxes_2026.json.

Writes:
  content_drafts/tourist-taxes-around-the-world-2026-data.final.md and .meta.json (then publish_article.py)
  site/data/tourist-taxes-2026.csv and docs/data/tourist-taxes-2026.csv (the downloadable data)

Every number comes from the facts ledger (data/facts/*.json) through the dataset; nothing is typed in here.
usage: .venv/bin/python ops/build_tax_report.py
"""
import csv
import json
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = json.loads((REPO / "data" / "tourist_taxes_2026.json").read_text())
SLUG = "tourist-taxes-around-the-world-2026-data"
CSV_NAME = "tourist-taxes-2026.csv"
PUBLISHED = date(2026, 10, 27)  # first publication; the citation keeps it
STAY = {p.stem.removeprefix("where-to-stay-in-"): p.name for p in (REPO / "site" / "articles").glob("where-to-stay-in-*.html")}
LABEL = {"percent": "Percentage of the room price", "flat_per_person_night": "Flat, per person per night",
         "flat_per_room_night": "Flat, per room per night", "tiered_by_rate": "Bands by room price",
         "tiered_by_star": "Bands by hotel class", "mixed": "Percentage plus flat charges", "none": "None",
         "unknown": "Not in our ledger"}
REGIONS = [("Asia", {"Japan", "South Korea", "China", "Hong Kong", "Taiwan", "Thailand", "Vietnam", "Malaysia",
                     "Singapore", "Indonesia"}),
           ("Europe", {"France", "Italy", "Spain", "Portugal", "Netherlands", "Germany", "Austria", "Czechia",
                       "Czech Republic", "Hungary", "Poland", "Croatia", "Greece", "Denmark", "Sweden", "Ireland",
                       "United Kingdom", "Iceland", "Switzerland", "Finland", "Türkiye", "Turkey"}),
           ("The Americas", {"United States", "Canada", "Mexico", "Brazil"}),
           ("Africa, the Middle East and Oceania", {"Morocco", "South Africa", "United Arab Emirates", "Australia",
                                                    "New Zealand"})]


def money(v, cur):
    return "" if v is None else f"{cur} {v:,.2f}"


def city_link(r):
    key = r["city"].lower().replace(", ", "-").replace(" ", "-").replace(".", "").replace("ó", "o").replace("ú", "u")
    return f"[{r['city']}]({STAY[key]})" if key in STAY else r["city"]


def main() -> None:
    # cities with no ledger fact are our gaps, not findings: they stay out of the public report
    rows = sorted([r for r in DATA["rows"] if r["structure"] != "unknown" and r["checked"]],
                  key=lambda r: (r["country"], r["city"]))
    computed = sorted([r for r in rows if r["example_status"] == "computed" and r["example_3n_2a_usd"] is not None],
                      key=lambda r: -r["example_3n_2a_usd"])
    # strongest evidence first: an official statement of none, then a negative finding
    none = sorted([r for r in rows if r["example_status"] == "none"],
                  key=lambda r: (0 if (r["none_basis"] or "").startswith("ledger states none") else 1, r["city"]))
    unclear = [r for r in rows if r["example_status"].startswith("ambiguous")]
    changes = [r for r in rows if r["changes_scheduled"]]
    fx = DATA["fx"]
    today = date.today()
    newest = max(r["checked"] for r in rows)

    # downloadable data
    cols = ["city", "country", "currency", "tax_name", "structure", "rule_text", "example_3n_2a",
            "example_3n_2a_usd", "example_status", "general_tax_note", "changes_scheduled", "checked", "sources"]
    for root in ("site", "docs"):
        out = REPO / root / "data" / CSV_NAME
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c] if c != "sources" else " ".join(s["url"] for s in (r["sources"] or r["other_sources"]))
                            for c in cols])

    top = computed[:5]
    L = []
    L.append(f"A hotel's quoted rate is rarely the whole bill. In most of the {len(rows)} cities below, a tourist, "
             "city or accommodation tax is added per person, per room or as a percentage of the price. This page "
             "puts them side by side: what each city charges, and what it adds to one standard stay, with the "
             "official source for every figure. Journalists and researchers may cite and reuse it with a link.")
    L.append("")
    L.append(f"*Data checked between 4 October and {date.fromisoformat(newest).strftime('%-d %B %Y')} at official "
             f"sources. Exchange rates: European Central Bank reference rates for {fx['date']}.*")
    L.append("")
    L.append("## Key findings")
    L.append("")
    L.append(f"- **The highest tax on our example stay** (3 nights, 2 adults, one room at US$200 a night before tax, "
             f"four-star where class matters): " + "; ".join(f"{r['city']}, about US${r['example_3n_2a_usd']:,.0f}"
                                                          for r in top) + ".")
    us = [r for r in computed if r["country"] == "United States"]
    if us:
        L.append(f"- **US cities top the table** because their hotel taxes are percentages of the room price: "
                 f"{len(us)} of the {len(computed)} cities we could compute are in the United States.")
    L.append(f"- **{len(none)} cities charge no accommodation-specific tax** in 2026 on the evidence we have, "
             "among them " + ", ".join(r["city"] for r in none[:8]) + " (VAT, GST or a service charge may still "
             "apply; see each city).")
    L.append(f"- **{len(changes)} cities have a change scheduled or under discussion**; the dated ones are listed "
             "under *What changes next*.")
    L.append("")
    L.append("## How to cite this data")
    L.append("")
    updated = "" if today == PUBLISHED else f", updated {today.strftime('%-d %B %Y')}"
    L.append(f"Gently Yonder, *Tourist taxes around the world 2026* (published {PUBLISHED.strftime('%-d %B %Y')}{updated}), "
             f"https://gentlyyonder.com/articles/{SLUG}.html")
    L.append("")
    L.append(f"Download the full dataset as a spreadsheet: [{CSV_NAME}](../data/{CSV_NAME}) "
             "(one row per city: the rule as published, the example, the general taxes kept separate, scheduled "
             "changes, the date checked and the official sources). If a figure here is wrong, our "
             "[corrections page](../corrections.html) says how to tell us, and every fix is logged there.")
    L.append("")
    L.append("## The example stay, and what counts")
    L.append("")
    L.append(f"- **The stay:** {DATA['example']}. The US$200 is converted to each local currency at the ECB "
             f"reference rate for {fx['date']}, and the tax is converted back at the same rate.")
    L.append("- **What counts:** taxes specific to accommodation (tourist taxes, city taxes, occupancy taxes, visitor "
             "levies). General VAT, GST and sales tax, and hotels' service charges, are listed separately for each "
             "city and are not in the example, because they apply to most purchases, not only to rooms.")
    L.append("- **Where we did not compute:** when the rule depends on something the example does not fix (which "
             "district, whether a band is per person or per room, whether the base includes VAT), we show the "
             "rule and leave the example blank rather than guess.")
    L.append("- **Sources:** each rate comes from the city, regional or national government, or the tax authority, "
             "and is recorded in our facts ledger with the date we checked it. See [how we verify](../methodology.html).")
    L.append("")
    L.append("## All cities at a glance")
    L.append("")
    L.append("Sorted by the tax on the example stay, highest first; cities without a computed figure follow.")
    L.append("")
    L.append("| City | Country | How it is charged | Tax on the example stay | ≈ US$ |")
    L.append("|---|---|---|---|---|")
    for r in computed + [r for r in rows if r not in computed]:
        if r["example_status"] == "computed":
            local, usd = money(r["example_3n_2a"], r["currency"]), (f"{r['example_3n_2a_usd']:,.2f}"
                                                                     if r["example_3n_2a_usd"] is not None else "")
        elif r["example_status"] == "none":
            local, usd = "None", "0"
        else:
            local, usd = "See the rule", ""
        L.append(f"| {city_link(r)} | {r['country']} | {LABEL.get(r['structure'], r['structure'])} | {local} | {usd} |")
    L.append("")
    L.append("## What changes next")
    L.append("")
    for r in sorted(changes, key=lambda r: r["city"]):
        L.append(f"- **{r['city']}:** {r['changes_scheduled']}")
    L.append("")
    for region, countries in REGIONS:
        rr = [r for r in rows if r["country"] in countries]
        if not rr:
            continue
        L.append(f"## {region}: the rules, city by city")
        L.append("")
        for r in rr:
            L.append(f"### {r['city']} tourist tax 2026")
            L.append("")
            L.append(f"**{r['tax_name']}.** {r['rule_text']}" if r["tax_name"] else r["rule_text"])
            if r["general_tax_note"]:
                L.append("")
                L.append(f"*Also on the bill:* {r['general_tax_note']}")
            if r["example_status"] == "computed":
                L.append("")
                L.append(f"*Example stay:* {money(r['example_3n_2a'], r['currency'])}"
                         + (f" (about US${r['example_3n_2a_usd']:,.2f})" if r["example_3n_2a_usd"] is not None else "")
                         + f". {r['example_basis']}")
            elif r["example_status"].startswith("ambiguous"):
                L.append("")
                L.append(f"*Example stay:* not computed: {r['example_status'].removeprefix('ambiguous: ')}")
            # a row with no official source (a negative finding from reporting) says so
            shown, label = (r["sources"], "Official sources") if r["sources"] else (r["other_sources"], "Sources (news reporting)")
            src = " · ".join(f"[{i + 1}]({s['url']})" for i, s in enumerate(shown[:3]))
            L.append("")
            L.append(f"*{label}:* {src}. Checked {date.fromisoformat(r['checked']).strftime('%-d %B %Y')}."
                     + (f" Our guide: {city_link(r)}." if city_link(r) != r["city"] else ""))
            L.append("")
    L.append("## Sources & further reading")
    L.append("")
    L.append("- Each city's official sources are linked under its rule above, and listed in the spreadsheet.")
    L.append(f"- European Central Bank euro foreign exchange reference rates for {fx['date']}, via frankfurter.app.")
    L.append("- [Hotel taxes around the world (2026)](hotel-taxes-around-the-world-2026.html): our guide to what the "
             "taxes mean when you compare hotel prices.")
    L.append("")
    L.append("*Taxes change, often on 1 January or 1 April. We recheck each figure on a schedule and log every change "
             "on our corrections page; check the city's own page before you rely on a figure for a booking.*")

    (REPO / "content_drafts" / f"{SLUG}.final.md").write_text(
        f"# Tourist Taxes Around the World 2026: City-by-City Data for {len(rows)} Cities\n\n" + "\n".join(L) + "\n")
    t = top[0]
    meta = {
        "title": f"Tourist Taxes Around the World 2026: City-by-City Data for {len(rows)} Cities",
        "slug": SLUG,
        "description": (f"Tourist and hotel taxes in {len(rows)} cities, 2026: the rule, what each adds to a 3-night "
                        "stay, scheduled changes and official sources. Free to cite, with a CSV."),
        "category": "Stay",
        "primary_keyword": "tourist tax by city 2026",
        "faq": [
            {"q": "Which city has the highest tourist tax on a hotel stay in 2026?",
             "a": (f"On our example stay (3 nights, 2 adults, one room at US$200 a night before tax), {t['city']} "
                   f"adds the most, about US${t['example_3n_2a_usd']:,.0f}, followed by "
                   + ", ".join(r["city"] for r in top[1:4]) + ".")},
            {"q": "Which cities charge no tourist tax?",
             "a": (f"On the evidence we have, {len(none)} of the {len(rows)} cities charge no accommodation-specific "
                   "tax in 2026, among them " + ", ".join(r["city"] for r in none[:6]) + "; VAT or GST may still "
                   "apply.")},
            {"q": "Is VAT or sales tax included in these figures?",
             "a": ("No. The figures cover taxes specific to accommodation; general VAT, GST and sales tax are listed "
                   "separately for each city.")},
            {"q": "Can I use this data in an article?",
             "a": ("Yes, with a link to this page. The full dataset is available as a spreadsheet, with the official "
                   "source and check date for every city.")},
        ],
    }
    (REPO / "content_drafts" / f"{SLUG}.meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    print(f"rows {len(rows)}: computed {len(computed)}, none {len(none)}, unclear {len(unclear)}, changes {len(changes)}")


if __name__ == "__main__":
    main()
