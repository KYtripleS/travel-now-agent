"""Link every hotel name in a stay guide to the hotel's checked Booking.com page (through Stay22),
the same page as its "Check rates" link, and keep the hotel's own website one tap away.

Since 2026-11-19 (competitor study: Travel Lemming and Earth Trekkers link hotel names to a booking
page, and in 30 days our bold names sent ~27 readers to hotels' own sites, where we earn nothing):
  - area bullets: the bold name links to the checked Booking.com page, and "Hotel's own site" is
    added after the rates link;
  - "at a glance" table and quick picks: the name links to the same page.
A hotel with no checked Booking.com page keeps its own website. Names are matched only to the page
already checked for that bullet, never by fuzzy search.

Readers get one tap from the table to the hotel, and Stay22's Spark, which
links words that have no link yet, finds nothing to match there: a name match
once sent a HOSHINOYA link to a different property.

Idempotent: a name that is already a link is left alone.

usage: python link_hotel_names.py           # dry run
       python link_hotel_names.py --write   # apply to site/ and docs/
"""
from __future__ import annotations

import html as htmllib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
ROOTS = (REPO / "site", REPO / "docs")
LI_RE = re.compile(r"<li><strong>(.*?)</strong>(.*?)</li>", re.S)


def official_links(page: str) -> dict[str, str]:
    """hotel name (as printed) -> its checked Booking.com page, else its own website, from the area sections."""
    out = {}
    for strong, body in LI_RE.findall(page):
        own = re.search(r'<a [^>]*href="([^"]+)"', strong)        # the name's link
        rates = re.search(r'class="gy-rates"[^>]*>\s*<a href="([^"]+)"', body)   # its checked Booking.com page
        if own or rates:
            if rates:
                out[htmllib.unescape(re.sub(r"<[^>]+>", "", strong)).strip()] = rates.group(1)
    return out


def _link(name_html: str, href: str) -> str:
    rel = "nofollow sponsored noopener" if "stay22.com" in href else "noopener"
    return f'<a class="gy-hotel-name" href="{href}" rel="{rel}" target="_blank">{name_html}</a>'


BULLET_RE = re.compile(r'<li><strong>(<a [^>]*>)(.*?)</a></strong>(.*?)</li>', re.S)
RATES_RE = re.compile(r'<span class="gy-rates"[^>]*>\s*<a href="([^"]+)"[^>]*>.*?</a></span>', re.S)
OWN_RE = re.compile(r' ?<span class="gy-own"><a class="gy-own-site"[^>]*>[^<]*</a></span>')


def bullets(page: str) -> tuple[str, int]:
    """Area bullets: the name -> its checked Booking.com page. Operator, 2026-11-19: no links to
    hotels' own websites; a hotel with no checked partner page is printed unlinked until one is checked."""
    n = 0

    def one(m: re.Match) -> str:
        nonlocal n
        tag, name, body = m.groups()
        r = RATES_RE.search(body)
        if r and r.group(1) in tag:
            return m.group(0)
        n += 1
        return f"<li><strong>{_link(name, r.group(1)) if r else name}</strong>{body}</li>"
    page = re.sub(r' data-own="[^"]*"', "", OWN_RE.sub("", page))
    return BULLET_RE.sub(one, page), n


def find_href(text: str, links: dict[str, str]) -> str | None:
    if text in links:
        return links[text]
    hits = [h for n, h in links.items() if text.startswith(n) or n.startswith(text)]   # "(our pick)", ", Autograph Collection"
    return hits[0] if len(hits) == 1 else None


def link_page(page: str) -> tuple[str, int]:
    page, n = bullets(page)
    links = official_links(page)
    if not links:
        return page, n

    def relink(m: re.Match) -> str:          # names linked to an own website before 2026-11-19
        nonlocal n
        href = find_href(htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip(), links)
        n += 1
        return _link(m.group(2), href) if href else m.group(2)
    page = re.sub(r'<a class="gy-hotel-name" href="((?!https://www\.stay22)[^"]+)" rel="noopener" target="_blank">(.*?)</a>', relink, page)

    def table(m: re.Match) -> str:
        nonlocal n
        t = m.group(0)
        if "<th>Hotel</th>" not in t or "<th>Tier</th>" not in t:
            return t

        def row(r: re.Match) -> str:
            nonlocal n
            cell = r.group(2)
            if "<a " in cell:
                return r.group(0)
            href = find_href(htmllib.unescape(re.sub(r"<[^>]+>", "", cell)).strip(), links)
            if not href:
                return r.group(0)
            n += 1
            return f"{r.group(1)}{_link(cell, href)}</td>"
        return re.sub(r"(<tr>\s*<td>)(.*?)</td>", row, t, flags=re.S)

    page = re.sub(r"<table>.*?</table>", table, page, flags=re.S)

    def qp(m: re.Match) -> str:
        nonlocal n
        href = find_href(htmllib.unescape(m.group(1)).strip(), links)
        if not href:
            return m.group(0)
        n += 1
        return f'<li><strong>{_link(m.group(1), href)}</strong><span class="gy-qp-meta">'
    page = re.sub(r'<li><strong>([^<]+)</strong><span class="gy-qp-meta">', qp, page)
    return page, n


def main() -> None:
    write = "--write" in sys.argv
    total = pages = 0
    for root in ROOTS:
        for f in sorted((root / "articles").glob("where-to-stay-*.html")):
            old = f.read_text(encoding="utf-8")
            new, n = link_page(old)
            if new != old:
                pages += 1
                total += n
                if write:
                    f.write_text(new, encoding="utf-8")
    print(f"hotel names: {'linked' if write else 'would link'} {total} in {pages} file(s)")


if __name__ == "__main__":
    main()
