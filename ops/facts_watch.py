"""Recheck due facts with a script first, so a model reads a source only when the script can't confirm it.

Each source in the ledger may carry "evidence": a short verbatim quote (or a list of quotes) copied
from that page when the fact was last checked. This script fetches every due source and looks for
its quotes (case, quotes, dashes and whitespace normalised). It also remembers a hash of each
page's text in ops/state/facts_watch.json, with the first day that exact text was seen.

A fact is CONFIRMED when every source that has evidence still shows all of it, at least one of those
sources is official/operator/publisher (or the fact's topic doesn't need one), and either the fact
is not short-lived (recheck_days unset or >= 30) or the page text has not changed since the fact was
last checked (its hash was first seen on or before that day).
Everything else is listed for a model, grouped by URL, with the reason (no evidence yet, blocked,
PDF, quote gone, short-lived and changed).

usage: .venv/bin/python ops/facts_watch.py [--days 14] [--write] [--ids PREFIX]
  --days N   facts due within N days (default 14, same as facts.py --due)
  --write    set checked=today and checked_by="script" on confirmed facts
  --ids P    only facts whose id starts with P
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import facts as F  # noqa: E402

CACHE = REPO / "ops" / "state" / "facts_watch.json"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SHORT_LIVED = 30


def norm(s: str) -> str:
    s = html.unescape(s).replace(" ", " ")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip().casefold()


def sha(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def fetch(url: str) -> tuple[str, str]:
    """(status, normalised text); status is 'ok', 'pdf', 'empty' or 'err:<reason>'."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,ja;q=0.8"})
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read(5_000_000)
    except Exception as e:  # noqa: BLE001
        return f"err:{getattr(e, 'code', '') or type(e).__name__}", ""
    if body[:4] == b"%PDF":
        return "pdf", ""
    t = body.decode("utf-8", "ignore")
    t = re.sub(r"(?s)<!--.*?-->|<(script|style|noscript)[^>]*>.*?</\1>", " ", t)  # old text often sits in comments
    t = norm(re.sub(r"<[^>]+>", " ", t))
    return ("ok" if len(t) > 300 else "empty"), t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=F.DUE_SOON)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    today = dt.date.today()
    horizon = today + dt.timedelta(days=a.days)
    due = [f for f in F.load() if f.get("status", "current") == "current" and f["id"].startswith(a.ids)
           and F.due_date(f) <= horizon]
    urls = sorted({s["url"] for f in due for s in f["sources"] if s.get("evidence")})
    with cf.ThreadPoolExecutor(12) as ex:
        pages = dict(zip(urls, ex.map(fetch, urls)))
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    confirmed, review = [], {}
    for f in due:
        with_ev = [s for s in f["sources"] if s.get("evidence")]
        reason = None
        if not with_ev:
            reason = "no evidence yet"
        else:
            kinds = set()
            for s in with_ev:
                st, text = pages[s["url"]]
                if st != "ok":
                    reason = st
                    break
                quotes = s["evidence"] if isinstance(s["evidence"], list) else [s["evidence"]]
                gone = [q for q in quotes if norm(q) not in text]
                if gone:
                    reason = f"quote gone: {gone[0][:60]!r}"
                    break
                kinds.add(s.get("kind"))
            if not reason and f.get("topic") in F.NEEDS_STRONG and not kinds & F.STRONG:
                reason = "evidence only on weak sources"
            if not reason and (f.get("recheck_days") or 999) < SHORT_LIVED:
                same = all(cache.get(s["url"], {}).get("sha") == sha(pages[s["url"]][1])
                           and cache[s["url"]]["since"] <= f["checked"] for s in with_ev)
                if not same:
                    reason = "short-lived fact and the page changed (or first run)"
        if reason:
            review.setdefault(f["sources"][0]["url"], []).append((f, reason))
        else:
            confirmed.append(f)
    for u, (st, text) in pages.items():
        if st == "ok" and cache.get(u, {}).get("sha") != sha(text):
            cache[u] = {"sha": sha(text), "since": today.isoformat()}
    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True) + "\n")

    if a.write and confirmed:
        ids = {f["id"] for f in confirmed}
        for path in sorted({f["_file"] for f in confirmed}):
            p = F.LEDGER / path
            d = json.loads(p.read_text(encoding="utf-8"))
            for x in d["facts"]:
                if x["id"] in ids:
                    x["checked"], x["checked_by"] = today.isoformat(), "script"
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_rev = sum(len(v) for v in review.values())
    print(f"{len(due)} due by {horizon}: {len(confirmed)} confirmed by script"
          f"{' (written)' if a.write else ''}, {n_rev} for a model, {len(review)} URLs")
    for u, items in sorted(review.items(), key=lambda kv: min(F.due_date(f) for f, _ in kv[1])):
        print(u)
        for f, why in items:
            print(f"  {F.due_date(f)} {f['id']}  [{why}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
