"""Stay Finder: which area of a city suits this trip, from our own stay guides.

Reads every published where-to-stay-in-<city>.html and pulls out what the
guide already states, in a fixed shape:
  - "The short answer" table: If you want... | Stay in | Why
  - each area's section: its heading, anchor and the hotels listed under it,
    with tier (splurge / comfortable / good value / budget) and the page's own
    verified Booking.com link (stay22.py)
  - "All 12 at a glance": Best for / Watch out for, by hotel name
  - the verdict's area link and the guide's dateModified

Nothing is invented or fetched live: no prices, ratings or availability. The
tool (site/tools/stay-finder.html, script in site/js/gy-finder.js) ranks the
areas with the open rules in RULES below and shows every point it gives.

Writes site/data/stay-finder.json (and docs/), and puts one pointer to the tool
under each guide's short-answer table.

usage: python build_stay_finder.py           # build data + pointers
       python build_stay_finder.py --report  # also print what was extracted per city
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent
SITE, DOCS = REPO / "site", REPO / "docs"
OUT = "data/stay-finder.json"

TIERS = {"splurge": 4, "comfortable": 3, "good value": 2, "budget": 1}

# priority -> (label, keywords). A keyword in the guide's "If you want..." line
# scores 3; in the "Why" line or the area heading, 1. The tool shows the reader
# the matched words with the points.
RULES = {
    "first": ("First trip, sights on foot", r"first (trip|visit|time)|everything easy|sights|on foot|walk(ing|able)|central(?! park)|old town|landmarks?|cent(re|er) of"),
    "night": ("Evenings out", r"evenings? out|night ?life|nights? out|bars?|lively|pubs?|clubs?|after dark|late[- ]night|all-hours"),
    "quiet": ("Quiet nights", r"quiet(er)?|calm|peace(ful)?|residential|(?<!greenwich )village|leafy|slower|gentler"),
    "food": ("Food and markets", r"food|restaurants?|markets?|eat(ing|eries)?|caf[eé]s?|dining|hawkers?|yatai"),
    "shop": ("Shopping", r"shop(s|ping)?|boutiques?|department stores?|malls?|fashion|designer"),
    "transit": ("Airport and train links", r"airport|station|trains?|rail|metro|subway|mrt|skytrain|shinkansen|skyliner|tram|transport|transit|ferry|express|bus(es)?\b"),
    "value": ("Lower prices", r"lower prices|budget|cheaper|better value|good value|for less|affordable"),
    "family": ("Families and space", r"famil(y|ies)|kids|children|parks?\b|theme park|zoo|space"),
    "water": ("Water and views", r"beach|seas?\b|seaside|harbou?r|river|waterfront|lake|canals?|bay\b|coast|views?|ocean|surf"),
    "culture": ("Museums and history", r"museums?|galler(y|ies)|\bart\b|history|historic|temples?|shrines?|cathedral|palace|castle|heritage|ruins|forums?|old[- ]\w+"),
}


def text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).replace(" ,", ",").replace(" .", ".") if el else ""


def tags_for(want: str, why: str, heading: str) -> dict[str, list]:
    """priority -> [points, the words that matched], so the tool can show its reason"""
    out = {}
    for key, (_, pat) in RULES.items():
        pat = rf"\b(?:{pat})\b"
        m = re.search(pat, want, re.I)
        if m:
            out[key] = [3, m.group(0)]
            continue
        m = re.search(pat, f"{why} {heading}", re.I)
        if m:
            out[key] = [1, m.group(0)]
    return out


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+", s.lower()) if w not in {"and", "the", "of", "de", "la", "le"}}


def parse(path: Path) -> dict | None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    h1 = text(soup.find("h1"))
    m = re.match(r"Where to Stay (?:in|for) (.+?)(?: \(\d{4}\)|:)", h1)
    if not m:
        return None
    city = m.group(1)
    modified = ""
    for s in soup.find_all("script", type="application/ld+json"):
        mm = re.search(r'"dateModified"\s*:\s*"([\d-]{10})', s.string or "")
        if mm:
            modified = mm.group(1); break
    short, glance, lead = None, {}, "If you want"
    for t in soup.find_all("table"):
        head = [text(th) for th in t.find_all("th")]
        if head and head[0].lower().startswith("if you") and short is None:
            lead = head[0].rstrip("….: ")          # "If you want" or "If you"
            short = [[text(td) for td in tr.find_all("td")] for tr in t.find_all("tr") if tr.find("td")]
        elif "Hotel" in head and "Tier" in head:
            ix = {h: i for i, h in enumerate(head)}
            for tr in t.find_all("tr"):
                tds = [text(td) for td in tr.find_all("td")]
                if len(tds) == len(head):
                    glance[tds[ix["Hotel"]]] = {"best": tds[ix.get("Best for", 0)], "watch": tds[ix.get("Watch out for", 0)]}
    if not short:
        return None
    sections = []                             # (h2 id, heading, [hotels])
    for h2 in soup.find_all("h2"):
        hotels = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            for li in sib.find_all("li") if sib.name in ("ul", "ol") else []:
                strong = li.find("strong")
                mt = re.match(r"\s*,\s*(splurge|comfortable|good value|budget)\b", str(strong.next_sibling or "")) if strong else None
                if not mt:
                    continue
                name = text(strong)
                rates = li.select_one(".gy-rates a[href]")
                g = glance.get(name) or next((v for k, v in glance.items() if k.startswith(name)), {})
                hotels.append({"name": name, "tier": TIERS[mt.group(1)],
                               "best": g.get("best", ""), "watch": g.get("watch", ""),
                               "rates": rates["href"] if rates else None})
        if hotels:
            sections.append((h2.get("id", ""), text(h2), hotels))
    areas, used = [], set()
    for row in short:
        if len(row) < 3:
            continue
        want, area, why = row[0], row[1], row[2]
        best, score = None, 0
        for i, (hid, head, _) in enumerate(sections):
            ov = len(_words(area) & _words(head.split(":")[0]))
            if ov > score and i not in used:
                best, score = i, ov
        hid, head, hotels = sections[best] if best is not None else ("", "", [])
        if best is not None:
            used.add(best)
            hotels = list(hotels)
            if " or " in area:                # "Bondi or Manly": both sections' hotels
                for i, (_, h2, more) in enumerate(sections):
                    if i not in used and _words(area) & _words(h2.split(":")[0]):
                        used.add(i); hotels += more
        areas.append({"name": area, "want": want, "why": why, "heading": head, "anchor": hid,
                      "tags": tags_for(want, why, head), "hotels": hotels})
    v = soup.select_one(".gy-verdict-cta a[href]")
    return {"slug": path.stem, "city": city, "url": f"articles/{path.name}", "checked": modified, "lead": lead,
            "area_rates": v["href"] if v and "stay22" in v["href"] else None,
            "tax_anchor": next((h.get("id") for h in soup.find_all("h2") if re.search(r"tax", text(h), re.I) and h.get("id")), ""),
            "areas": areas}


POINTER_RE = re.compile(r'\n?<p class="gy-finder-pointer".*?</p>', re.S)


def pointer(slug: str) -> str:
    return (f'<p class="gy-finder-pointer">Not sure which area? <a href="../tools/stay-finder.html?city={slug}">'
            f"Rank these areas for your trip</a>: pick what matters and see the reasons.</p>")


def add_pointer(path: Path, slug: str) -> bool:
    s = path.read_text(encoding="utf-8")
    new = POINTER_RE.sub("", s)
    m = re.search(r'<h2 id="the-short-answer"[^>]*>.*?</table>(\s*</div>)?', new, re.S)
    if not m:
        return False
    new = new[:m.end()] + "\n" + pointer(slug) + new[m.end():]
    if new != s:
        path.write_text(new, encoding="utf-8")
    return True


def main() -> None:
    cities, skipped = [], []
    for p in sorted((SITE / "articles").glob("where-to-stay-in-*.html")):
        d = parse(p)
        if not d or len(d["areas"]) < 3 or not any(a["hotels"] for a in d["areas"]):
            skipped.append(p.stem); continue
        cities.append(d)
    cities.sort(key=lambda d: d["city"])
    data = {"_doc": "Built by build_stay_finder.py from the stay guides; edit the guides, not this file.",
            "rules": {k: {"label": v[0]} for k, v in RULES.items()},
            "tiers": {str(v): k for k, v in TIERS.items()},
            "cities": cities}
    for root in (SITE, DOCS):
        (root / OUT).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ptr = 0
    for d in cities:
        for root in (SITE, DOCS):
            ptr += add_pointer(root / d["url"], d["slug"])
    print(f"stay finder: {len(cities)} cities, {sum(len(d['areas']) for d in cities)} areas, "
          f"{sum(len(a['hotels']) for d in cities for a in d['areas'])} hotels; {ptr // 2} pointers; "
          f"skipped {skipped}")
    if "--report" in sys.argv:
        for d in cities:
            nh = sum(len(a["hotels"]) for a in d["areas"])
            miss = [a["name"] for a in d["areas"] if not a["hotels"]]
            print(f"  {d['city']:16} areas {len(d['areas'])} hotels {nh:2} rates {sum(1 for a in d['areas'] for h in a['hotels'] if h['rates']):2}"
                  f" checked {d['checked']}" + (f"  no hotels: {miss}" if miss else ""))


if __name__ == "__main__":
    main()
