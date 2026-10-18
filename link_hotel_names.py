"""Link every hotel name in a stay guide's "at a glance" table and quick picks
to the same official website its own section already links (or, where the
section names no website, its checked Booking.com page).

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
    """hotel name (as printed) -> its official website, from the area sections."""
    out = {}
    for strong, body in LI_RE.findall(page):
        own = re.match(r'<a href="([^"]+)"', strong)              # the hotel's own website
        rates = re.search(r'class="gy-rates"[^>]*>\s*<a href="([^"]+)"', body)   # else its checked Booking.com page
        if own or rates:
            out[htmllib.unescape(re.sub(r"<[^>]+>", "", strong)).strip()] = own.group(1) if own else rates.group(1)
    return out


def _link(name_html: str, href: str) -> str:
    rel = "nofollow sponsored noopener" if "stay22.com" in href else "noopener"
    return f'<a class="gy-hotel-name" href="{href}" rel="{rel}" target="_blank">{name_html}</a>'


def find_href(text: str, links: dict[str, str]) -> str | None:
    if text in links:
        return links[text]
    hits = [h for n, h in links.items() if text.startswith(n) or n.startswith(text)]   # "(our pick)", ", Autograph Collection"
    return hits[0] if len(hits) == 1 else None


def link_page(page: str) -> tuple[str, int]:
    links = official_links(page)
    if not links:
        return page, 0
    n = 0

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
