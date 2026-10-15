"""Put verified, time-limited offers from data/promotions.json on their pages,
and take them off again when they end or go unchecked.

Rules, in order; an offer that fails any of them is not shown:
  - verification.status is "verified", with at least one source URL
  - it was checked within verification.recheck_days (an unchecked offer is not
    presented as valid)
  - starts_at and ends_at parse, carry a UTC offset, and ends_at is in the future
  - the page exists and content_classes says it is "eligible" (no offers on
    historical or trust pages)
  - a coupon code is printed only when code_verified is true
  - an affiliate CTA links only to a partner the site already works with, and
    gets rel="nofollow sponsored noopener"; a public scheme links to its source
    with plain rel="noopener"

No deadline is ever invented: an offer without ends_at is refused, and a live
countdown appears only when "countdown" is true. gy-reveal.js runs the
countdown from the fixed ends_at in the markup, so a reload never resets it,
and hides the offer in the reader's browser the moment it ends.

The box goes after the page's verdict and its promise line (add_aeo.py) or,
failing that, before the first h2. Idempotent: every run removes all gy-promo boxes and re-renders
the ones still valid.

usage: python promotions.py           # update site/ and docs/
       python promotions.py --check   # report only; exit 1 if an offer is due a recheck
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import content_classes

REPO = Path(__file__).resolve().parent
DATA = REPO / "data" / "promotions.json"
ROOTS = (REPO / "site", REPO / "docs")
KNOWN_PARTNER_HOSTS = ("stay22.com", "tpx.lu", "tp.st", "sjv.io", "awin1.com", "amazon.com")
KINDS = {"public_scheme", "affiliate_offer", "coupon"}
BOX_RE = re.compile(r'\n?<aside class="gy-promo"[^>]*>.*?</aside>', re.S)


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return d if d.tzinfo else None              # a deadline without an offset is ambiguous


def problems(p: dict, now: datetime, today: date) -> list[str]:
    """Why an offer may not be shown; an empty list means it may."""
    out = []
    v = p.get("verification") or {}
    if p.get("kind") not in KINDS:
        out.append(f"unknown kind {p.get('kind')!r}")
    if v.get("status") != "verified" or not v.get("sources"):
        out.append("not verified at a source")
    try:
        age = (today - date.fromisoformat(v.get("checked", ""))).days
        if age > int(v.get("recheck_days", 0)):
            out.append(f"last checked {v['checked']}, {age} days ago (recheck every {v.get('recheck_days')})")
    except ValueError:
        out.append("no valid checked date")
    start, end = _parse(p.get("starts_at")), _parse(p.get("ends_at"))
    if end is None:
        out.append("no verified ends_at with a UTC offset")
    elif end <= now:
        out.append(f"ended {p['ends_at']}")
    if p.get("starts_at") and start is None:
        out.append("starts_at does not parse or has no offset")
    if start and end and start >= end:
        out.append("starts_at is not before ends_at")
    if p.get("coupon_code") and not p.get("code_verified"):
        out.append("coupon code not verified (it would be hidden, but fix the data)")
    aff = p.get("affiliate")
    if aff:
        host = re.sub(r"^https?://([^/]+).*", r"\1", aff.get("url", ""))
        if not any(host == h or host.endswith("." + h) for h in KNOWN_PARTNER_HOSTS):
            out.append(f"affiliate host {host!r} is not a partner the site already uses")
    elif not p.get("url"):
        out.append("no destination URL")
    return out


def _fmt_day(d: datetime) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def render(p: dict) -> str:
    e = lambda s: html.escape(str(s), quote=True)
    start, end = _parse(p.get("starts_at")), _parse(p["ends_at"])
    v = p["verification"]
    checked = date.fromisoformat(v["checked"])
    attrs = (f'class="gy-promo" data-promo="{e(p["id"])}" data-ends="{e(p["ends_at"])}"'
             + (f' data-starts="{e(p["starts_at"])}"' if start else "")
             + (' data-countdown="1"' if p.get("countdown") else "")
             + (f' data-left-prefix="{e(p["countdown_prefix"])} "' if p.get("countdown_prefix") else "")
             + f' data-precision="{e(p.get("precision", "day"))}"')
    when = p.get("end_text") or f"Ends {_fmt_day(end)}"
    when += f" ({e(p.get('timezone_label', ''))})" if p.get("timezone_label") else ""
    if p.get("ends_early_if"):
        when += f", or earlier if {e(p['ends_early_if'])}"
    parts = [f"<aside {attrs}>",
             f'<p class="gy-promo-label">Time-limited · checked {checked.day} {checked.strftime("%B %Y")}</p>',
             f'<p class="gy-promo-title"><strong>{e(p["title"])}</strong></p>',
             f'<p class="gy-promo-benefit">{e(p["benefit"])}</p>',
             f'<p class="gy-promo-when">{when}.<span class="gy-promo-left" hidden></span></p>']
    if p.get("eligibility"):
        parts.append('<ul class="gy-promo-terms">' + "".join(f"<li>{e(x)}</li>" for x in p["eligibility"]) + "</ul>")
    if p.get("coupon_code") and p.get("code_verified"):
        parts.append(f'<p class="gy-promo-code">Code: <code>{e(p["coupon_code"])}</code> '
                     f'<button type="button" class="gy-promo-copy" data-code="{e(p["coupon_code"])}">Copy code</button></p>')
    aff = p.get("affiliate")
    if aff:
        cta = (f'<a class="gy-promo-cta" href="{e(aff["url"])}" rel="nofollow sponsored noopener" '
               f'target="_blank">{e(p.get("cta_label", "Check This Offer"))} →</a>')
    else:
        cta = (f'<a class="gy-promo-cta" href="{e(p["url"])}" rel="noopener" '
               f'target="_blank">{e(p.get("cta_label", "Check This Offer"))} →</a>')
    parts.append(f'<p class="gy-promo-action">{cta}</p>')
    if p.get("how_to_claim"):
        parts.append(f'<p class="gy-promo-note">{e(p["how_to_claim"])}'
                     + (" We earn a commission if you book through this link." if aff else
                        " This is a public scheme; we earn nothing from it.") + "</p>")
    parts.append("</aside>")
    return "\n".join(parts)


def place(page: str, boxes: list[str]) -> str:
    page = BOX_RE.sub("", page)
    if not boxes:
        return page
    block = "\n" + "\n".join(boxes)
    m = re.search(r'<aside class="gy-verdict".*?</aside>(\s*<p class="gy-promise".*?</p>)?', page, re.S)
    if m:
        return page[:m.end()] + block + page[m.end():]
    m = re.search(r"<h2[ >]", page)
    if not m:
        raise ValueError("no verdict and no h2 to place the offer before")
    return page[:m.start()] + block.lstrip("\n") + "\n" + page[m.start():]


def main() -> int:
    check_only = "--check" in sys.argv
    now, today = datetime.now(timezone.utc), date.today()
    promos = json.loads(DATA.read_text())["promotions"]
    classes = content_classes.load()
    ids = [p["id"] for p in promos]
    if len(ids) != len(set(ids)):
        print("duplicate promotion ids"); return 1
    by_page: dict[str, list[str]] = {}
    due = 0
    for p in promos:
        bad = problems(p, now, today)
        if bad:
            due += any("last checked" in b for b in bad)
            print(f"  hold  {p['id']}: " + "; ".join(bad))
            continue
        print(f"  show  {p['id']} until {p['ends_at']} on {len(p['pages'])} page(s)")
        for rel in p["pages"]:
            if classes.get(rel) != "eligible":
                print(f"        skip {rel}: class {classes.get(rel, 'missing')}")
                continue
            by_page.setdefault(rel, []).append(render(p))
    if check_only:
        return 1 if due else 0
    targets = set(by_page)
    for root in ROOTS:                       # pages that carry an old box but should not now
        for f in root.glob("articles/*.html"):
            if 'class="gy-promo"' in f.read_text(encoding="utf-8"):
                targets.add(f.relative_to(root).as_posix())
    changed = 0
    for rel in sorted(targets):
        for root in ROOTS:
            f = root / rel
            if not f.exists():
                continue
            old = f.read_text(encoding="utf-8")
            new = place(old, by_page.get(rel, []))
            if new != old:
                f.write_text(new, encoding="utf-8"); changed += 1
    print(f"promotions: {sum(map(len, by_page.values()))} box(es) on {len(by_page)} page(s); {changed} file(s) changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
