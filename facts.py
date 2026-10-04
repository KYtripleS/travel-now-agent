#!/usr/bin/env python3
"""The facts ledger: every fact we have checked, where we checked it, and when to check it again.

Articles are where readers meet our facts; this ledger is where the facts live. Each one carries its
source and the day it was confirmed, and names the pages that state it, so a change is made once and
every page that repeats it can be found.

Files: data/facts/<place>.json, one per place ("world.json" for facts that span places).

  {"place": "Hong Kong", "facts": [ {...}, ... ]}

A fact:
  id            stable and dotted, e.g. "hk.airport-express.fare-hong-kong"
  topic         one of TOPIC_DAYS below; it sets how soon the fact goes stale
  claim         one plain sentence: exactly what we may say in public
  value         optional: the numbers in the claim, as data
  sources       [{"url", "kind", "title"}]; kind is one of KINDS
  checked       YYYY-MM-DD: the day the claim was last confirmed at a source
  recheck_days  optional: overrides the topic's default
  status        "current" (default) or "superseded"
  superseded_by for a superseded fact: the id that replaced it, and "changed" (YYYY-MM-DD)
  used_in       {"articles/x.html": ["exact text", ...]}: pages that state the fact, and strings
                that must appear in each (matched after tags, entities and curly quotes are removed)
  watch         optional regex (case-sensitive): pages that match it but are not in used_in are
                listed by --watch; aim it at statements of the value, not every mention
  note          optional: anything a future checker should know

Usage:
  python facts.py            check everything
  python facts.py --due      list facts due for a recheck in the next 14 days
  python facts.py --watch    also list pages that mention a watched fact but are not registered
  python facts.py --show hk. print the facts whose id starts with "hk."
  python facts.py --strict   also fail when a fact is overdue

Exit code 1 when a fact is malformed or a page no longer says what the ledger says
(and, with --strict, when a fact is overdue).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "data" / "facts"
SITE = ROOT / "site"

# How long a fact stays fresh, by topic (days)
TOPIC_DAYS = {
    "entry": 60,      # entry rules, arrival cards, visas
    "partner": 90,    # who we earn from, and how
    "price": 90,      # hotel, ticket and tour prices
    "fare": 180,      # public-transport fares
    "tax": 180,       # taxes and service charges
    "transport": 180,  # times, routes, services
    "hotel": 180,     # open, renamed, rooms, location
    "place": 180,     # attractions, opening hours
    "stat": 365,      # arrivals, surveys
    "history": 3650,  # opening dates and other settled history
}
KINDS = {
    "official": "a government body or the operator of the service",
    "operator": "the business itself (a hotel's own site)",
    "publisher": "the original publisher of a statistic or survey",
    "news": "a news report",
    "reference": "an encyclopaedia (Wikipedia)",
    "secondary": "a blog, aggregator or booking site",
}
STRONG = {"official", "operator", "publisher"}
NEEDS_STRONG = {"entry", "fare", "tax", "price", "partner"}
DUE_SOON = 14
REQUIRED = ("id", "topic", "claim", "sources", "checked")


def page_text(path: Path) -> str:
    t = path.read_text(encoding="utf-8")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = t.replace(" ", " ").replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'")
                  .replace("“", '"').replace("”", '"').replace(" ", " "))


def load() -> list[dict]:
    facts = []
    for f in sorted(LEDGER.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for fact in data.get("facts", []):
            fact["_file"] = f.name
            fact["_place"] = data.get("place", f.stem)
            facts.append(fact)
    return facts


def due_date(fact: dict) -> dt.date:
    days = fact.get("recheck_days") or TOPIC_DAYS.get(fact.get("topic"), 180)
    return dt.date.fromisoformat(fact["checked"]) + dt.timedelta(days=days)


def check(facts: list[dict], today: dt.date) -> tuple[list[str], list[str], list[tuple[dt.date, dict]]]:
    errors, warnings, due = [], [], []
    seen: set[str] = set()
    texts: dict[str, str] = {}
    for f in facts:
        fid = f.get("id", f"<no id in {f['_file']}>")
        for key in REQUIRED:
            if not f.get(key):
                errors.append(f"{fid}: missing {key}")
        if fid in seen:
            errors.append(f"{fid}: duplicate id")
        seen.add(fid)
        if f.get("topic") not in TOPIC_DAYS:
            errors.append(f"{fid}: unknown topic {f.get('topic')!r}")
        try:
            checked = dt.date.fromisoformat(f.get("checked", ""))
            if checked > today:
                errors.append(f"{fid}: checked date {checked} is in the future")
        except ValueError:
            errors.append(f"{fid}: checked must be YYYY-MM-DD")
            continue
        kinds = set()
        for s in f.get("sources", []):
            if not str(s.get("url", "")).startswith("https://"):
                errors.append(f"{fid}: source without an https url")
            if s.get("kind") not in KINDS:
                errors.append(f"{fid}: unknown source kind {s.get('kind')!r}")
            kinds.add(s.get("kind"))
        status = f.get("status", "current")
        if status not in ("current", "superseded"):
            errors.append(f"{fid}: status must be current or superseded")
        if status == "superseded":
            if not f.get("superseded_by"):
                errors.append(f"{fid}: superseded without superseded_by")
            if f.get("used_in"):
                errors.append(f"{fid}: superseded, but still listed as used on pages")
            continue
        if f.get("topic") in NEEDS_STRONG and not kinds & STRONG:
            warnings.append(f"{fid}: a {f['topic']} fact with no official or operator source")
        d = due_date(f)
        if d <= today + dt.timedelta(days=DUE_SOON):
            due.append((d, f))
        for page, needles in (f.get("used_in") or {}).items():
            p = SITE / page
            if not p.exists():
                errors.append(f"{fid}: used_in page {page} does not exist")
                continue
            text = texts.setdefault(page, page_text(p))
            for needle in needles:
                if norm(needle) not in text:
                    errors.append(f"{fid}: {page} no longer says {needle!r}")
    for f in facts:
        if f.get("status") == "superseded" and f.get("superseded_by") not in seen:
            errors.append(f"{f['id']}: superseded_by {f.get('superseded_by')!r} is not in the ledger")
    return errors, warnings, sorted(due, key=lambda x: x[0])


def watch(facts: list[dict]) -> list[str]:
    pages = sorted(SITE.glob("articles/*.html")) + sorted(SITE.glob("countries/**/*.html")) + \
        sorted(SITE.glob("cities/**/*.html"))
    texts = {str(p.relative_to(SITE)): page_text(p) for p in pages}
    out = []
    for f in facts:
        if not f.get("watch") or f.get("status") == "superseded":
            continue
        rx = re.compile(f["watch"])             # case-sensitive; write (?i) in the pattern when needed
        known = set((f.get("used_in") or {}).keys())
        for page, text in texts.items():
            if page in known:
                continue
            m = rx.search(text)
            if m:
                out.append(f"{f['id']}: {page} mentions it: ...{text[max(0, m.start() - 60):m.end() + 80]}...")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    today = dt.date.today()
    facts = load()
    if a.show:
        for f in facts:
            if f.get("id", "").startswith(a.show):
                print(json.dumps({k: v for k, v in f.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))
        return 0
    errors, warnings, due = check(facts, today)
    overdue = [(d, f) for d, f in due if d < today]
    if a.due:
        for d, f in due:
            print(f"{d}  {f['id']}: {f['claim']}")
        return 0
    current = [f for f in facts if f.get("status", "current") == "current"]
    places = sorted({f["_place"] for f in facts})
    used = sum(1 for f in current if f.get("used_in"))
    print(f"facts ledger: {len(current)} current, {len(facts) - len(current)} superseded, "
          f"{len(places)} places ({', '.join(places)})")
    print(f"  on pages: {used}   strong sources: "
          f"{sum(1 for f in current if {s.get('kind') for s in f.get('sources', [])} & STRONG)}/{len(current)}")
    for d, f in due:
        print(f"  {'OVERDUE' if d < today else 'due'} {d}: {f['id']}")
    for w in warnings:
        print(f"  warning: {w}")
    for e in errors:
        print(f"  ERROR: {e}")
    if a.watch:
        hits = watch(facts)
        print(f"  watched mentions not registered: {len(hits)}")
        for h in hits:
            print(f"    {h}")
    if not errors and not (a.strict and overdue):
        print("  ok")
    return 1 if errors or (a.strict and overdue) else 0


if __name__ == "__main__":
    sys.exit(main())
