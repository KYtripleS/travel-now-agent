"""Register a finished stay guide in every registry: stay22.PAGES + HOTELS, add_aeo V + QUICK_PICKS +
CITY_RATES, inject_tp, add_internal_links ARTICLES + LINKS, site_taxonomy, llms.txt (site + docs) and
the facts ledger. Idempotent: skips a registry that already names the slug.

The registration file (schema in prompts/stay_brief.md) is read from content_drafts/stay/<city>.json,
or from the path given with --reg.

usage: .venv/bin/python ops/register_stay.py <city> <City Name> <country-facts-file> <Country place name> [--reg FILE]
e.g.   .venv/bin/python ops/register_stay.py rome Rome italy Italy
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if a != "--reg"]
reg = Path(sys.argv[sys.argv.index("--reg") + 1]) if "--reg" in sys.argv else None
if reg:
    args.remove(str(reg))
city, name, facts_file, place = args[:4]
R = json.loads((reg or REPO / "content_drafts" / "stay" / f"{city}.json").read_text())
slug = R["slug"]; art = f"articles/{slug}.html"
q = lambda s: json.dumps(s, ensure_ascii=False)


def insert_after(path, anchor, text, marker):
    p = REPO / path; s = p.read_text()
    if marker in s:
        print(f"  skip {path} (already has {marker[:40]})"); return
    assert s.count(anchor) == 1, (path, anchor[:60], s.count(anchor))
    p.write_text(s.replace(anchor, anchor + text, 1)); print(f"  + {path}")


def insert_before_close(path, start, text, marker):
    p = REPO / path; s = p.read_text()
    if marker in s:
        print(f"  skip {path} (already has {marker[:40]})"); return
    i = s.index(start); j = s.index("\n}\n", i)
    p.write_text(s[:j] + "\n" + text.rstrip("\n") + s[j:]); print(f"  + {path}")


st = R["stay22"]
insert_after("stay22.py", 'address="Times Square, New York, NY, USA"),\n',
             f'    {q(slug)}: dict(area={q(st["area"])}, lat={st["lat"]}, lng={st["lng"]}, zoom={st.get("zoom", 15)},\n'
             f'{" " * (len(slug) + 16)}address={q(st["address"])}),\n', f'{q(slug)}: dict(area=')
hl = [f"    # {name} (Booking.com pages confirmed by hotel name and city)"]
for h, u in R["hotels"].items():
    hl.append(f"    {q(h)}: " + (f'_B + {q(u.split("/hotel/", 1)[1])},' if u else "None,"))
insert_before_close("stay22.py", "HOTELS = {", "\n".join(hl) + "\n", f"# {name} (Booking.com")

v = R["verdict"]
insert_after("add_aeo.py", 'cta=_stay_cta("where-to-stay-in-new-york", "See hotels around Times Square")),\n',
             f'    {q(slug)}: dict(\n        text={q(v["text"])},\n        link_text={q(v["link_text"])},\n'
             f'        cta=_stay_cta({q(slug)}, {q(v["cta_label"])})),\n', f"cta=_stay_cta({q(slug)}")
insert_after("add_aeo.py", '"where-to-stay-in-new-york": ["Arlo Midtown", "Washington Square Hotel", "Ace Hotel Brooklyn"],\n',
             f'    {q(slug)}: {q(R["verdict_hotels"])},\n', f"    {q(slug)}: [")
insert_after("add_aeo.py", '("New York", "where-to-stay-in-new-york", None, None),\n',
             f"        ({q(name)}, {q(slug)}, None, None),\n", f"({q(name)}, {q(slug)}, None, None)")
insert_after("inject_tp.py", '"Before you land in New York", ["tiqets", "airalo", "aviasales"]),\n',
             f'    {q(art)}: cta(\n        "Before you land in {name}", ["tiqets", "welcomepickups", "airalo"]),\n',
             f"{q(art)}: cta(")
title = f"Where to Stay in {name}"
insert_after("add_internal_links.py",
             '"Six areas from Midtown to Brooklyn, 12 hotels, the 14.75% hotel tax and the free bus from LaGuardia.",\n    ),\n',
             f"    {q(art)}: (\n        {q(title)},\n        {q(R['card_hook'])},\n    ),\n", f"    {q(art)}: (\n")
sys.path.insert(0, str(REPO)); import add_internal_links as _ail  # noqa: E402
links = [l for l in R["related"] if l in _ail.ARTICLES and l != art][:5]
insert_after("add_internal_links.py",
             '    "articles/where-to-stay-in-new-york.html": [\n        "articles/best-esim-usa-2026.html",\n        "articles/hotel-booking-sites-comparison.html",\n        "articles/travel-insurance-compared.html",\n        "articles/airalo-vs-holafly-vs-saily.html",\n        "articles/where-to-stay-in-paris.html",\n    ],\n',
             f"    {q(art)}: [\n" + "".join(f"        {q(l)},\n" for l in links) + "    ],\n", f"    {q(art)}: [\n")
insert_after("site_taxonomy.py", '    "where-to-stay-in-new-york": "Stay",\n', f'    {q(slug)}: "Stay",\n', f'{q(slug)}: "Stay"')
for root in ("site", "docs"):
    p = REPO / root / "llms.txt"; s = p.read_text()
    if f"/{slug}.html" in s:
        print(f"  skip {root}/llms.txt"); continue
    lines = s.split("\n"); i = next(k for k, l in enumerate(lines) if "/where-to-stay-in-new-york.html" in l)
    lines.insert(i + 1, R["llms_line"]); p.write_text("\n".join(lines)); print(f"  + {root}/llms.txt")

KINDS = ("official", "operator", "publisher", "news", "reference", "secondary", "comparison")
fp = REPO / "data/facts" / f"{facts_file}.json"
d = json.loads(fp.read_text()) if fp.exists() else {"place": place, "facts": []}
have = {f["id"]: f for f in d["facts"]}
elsewhere = {}
for other in (REPO / "data/facts").glob("*.json"):
    if other != fp:
        for f in json.loads(other.read_text())["facts"]:
            elsewhere[f["id"]] = other
new = []
for f in R["facts"]:
    for s in f.get("sources", []):
        if s.get("kind") not in KINDS:
            s["kind"] = "secondary"
        if s.get("url", "").startswith("http://"):
            s["url"] = "https://" + s["url"][7:]
    if f["id"] in have:                 # shared fact: add this page's usage and any new sources
        x = have[f["id"]]
        x.setdefault("used_in", {}).update(f.get("used_in", {}))
        urls = {s["url"] for s in x["sources"]}
        x["sources"] += [s for s in f.get("sources", []) if s["url"] not in urls]
        continue
    if f["id"] in elsewhere:            # shared fact in another file (e.g. eu.etias.status)
        op = elsewhere[f["id"]]; raw = op.read_text(); od = json.loads(raw)
        for x in od["facts"]:
            if x["id"] == f["id"]:
                x.setdefault("used_in", {}).update(f.get("used_in", {}))
        op.write_text(json.dumps(od, indent=1 if '\n "' in raw[:50] else 2, ensure_ascii=False) + "\n")
        print(f'  ~ merged {f["id"]} into {op.name}'); continue
    for x in f.get("used_in", {}).values():
        x[:] = [p.replace("...", "").strip() for p in x]
    new.append(f)
d["facts"] += new
fp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print(f"  + {len(new)} facts -> {fp.name}")
