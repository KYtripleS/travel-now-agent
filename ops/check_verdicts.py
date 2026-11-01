"""Check drafted verdicts (content_drafts/verdicts/batch*.json) against their pages, then merge the
ones that pass into data/verdicts_extra.json (read by add_aeo.py).

A verdict passes when: its button's href is a sponsored link already inside the page's article; every
evidence phrase is on the page; it is 20-60 words with no banned phrase or first-person visit claim;
and the partner its label names is the one the link goes to.

usage: .venv/bin/python ops/check_verdicts.py [--merge]
"""
import glob
import html
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
BANNED = re.compile(r"hidden gem|magical|must-see|bucket list|secret spot|off the beaten path|instagram-worthy|"
                    r"guarantee|\bI\b|\bwe (stayed|visited|loved|tried)\b", re.I)
# partner named in a label -> substrings its link must contain
PARTNERS = {"airalo": "airalo", "saily": "saily", "holafly": "sjv.io", "klook": "klook", "viator": "viator",
            "getyourguide": "getyourguide", "kkday": "kkday", "booking.com": "booking", "amazon": "amazon.",
            "trip.com": "trip", "kiwitaxi": "kiwitaxi", "discovercars": "discovercars", "hostelworld": "hostelworld",
            "omio": "omio", "12go": "12go", "airhelp": "airhelp", "safetywing": "safetywing", "tiqets": "tiqets",
            "welcome pickups": "tpx.lu", "aviasales": "aviasales", "stay22": "stay22", "agoda": "agoda",
            "radical storage": "radicalstorage", "kiwi.com": "kiwi", "nomatic": "nomatic", "kiwitaxi": "kiwitaxi"}
norm = lambda t: re.sub(r"\s+", " ", t.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def check(slug: str, v: dict) -> list[str]:
    p = REPO / "site/articles" / f"{slug}.html"
    if not p.exists():
        return ["no such page"]
    soup = BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser")
    art = soup.select_one("section.article")
    text = norm(art.get_text(" ", strip=True))
    errs = []
    kind, label, href = v["cta"]
    href = html.unescape(href)
    links = {a["href"] for a in art.select("a[rel~=sponsored]")}
    if kind != "href" or href not in links:
        errs.append("button href is not a sponsored link on the page")
    words = len(v["text"].split())
    if not 20 <= words <= 60:
        errs.append(f"{words} words")
    if BANNED.search(v["text"]) or BANNED.search(label):
        errs.append("banned or first-person wording: " + BANNED.search(v["text"] + " " + label).group(0))
    for e in v.get("evidence", []):
        if norm(e) not in text:
            errs.append(f"evidence not on page: {e[:60]}")
    named = [k for k in PARTNERS if k in label.lower()]
    if not named:
        errs.append("label names no partner")
    elif not any(PARTNERS[k] in href.lower() for k in named):
        errs.append(f"label names {named} but link is {href[:50]}")
    return errs


def main() -> None:
    merged, failed = {}, {}
    for f in sorted(glob.glob(str(REPO / "content_drafts/verdicts/batch*.json"))):
        for slug, v in json.loads(Path(f).read_text()).items():
            if slug.startswith("_"):
                continue
            errs = check(slug, v)
            if errs:
                failed[slug] = errs
            else:
                kind, label, href = v["cta"]
                merged[slug] = {"text": v["text"], "cta": [kind, label, html.unescape(href)]}
    print(f"pass {len(merged)}   fail {len(failed)}")
    for s, e in failed.items():
        print(f"  FAIL {s}: {'; '.join(e)}")
    if "--merge" in sys.argv:
        out = REPO / "data/verdicts_extra.json"
        out.write_text(json.dumps(dict(sorted(merged.items())), indent=1, ensure_ascii=False) + "\n")
        print("wrote", out.relative_to(REPO))


if __name__ == "__main__":
    main()
