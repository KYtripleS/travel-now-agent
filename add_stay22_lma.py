"""Stay22's LetMeAllez script (LinkSwap, Spark and Nova) on the pages in PAGES,
and nowhere else.

LinkSwap turns plain links to its providers (Booking.com, Expedia, Agoda,
GetYourGuide and others) into Stay22 links; our Travelpayouts links (Klook,
Airalo, Saily) are not on its list. Spark links words that have no link yet,
and Nova opens a hotel offer in a new tab for readers who look ready to book.

Spark can link a hotel name to the wrong property (a name match once sent a
HOSHINOYA link to another hotel), so the script runs on one page until we have
seen what Spark adds there; PAGES grows only after that check.

usage: python add_stay22_lma.py           # dry run
       python add_stay22_lma.py --write   # apply to site/ and docs/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
ROOTS = (REPO / "site", REPO / "docs")
LMA_ID = "6ad4bf479bf3c9ce439c24e8"           # public: it ships in every page that runs the script
PAGES = [
    "articles/where-to-stay-in-rome.html",    # trial page, 2026-10-18
]
BEGIN = "<!-- BEGIN Stay22 LetMeAllez (managed by add_stay22_lma.py) -->"
END = "<!-- END Stay22 LetMeAllez -->"
BLOCK = f"""{BEGIN}
<script>
  (function (s, t, a, y, twenty, two) {{
    s.Stay22 = s.Stay22 || {{}};
    s.Stay22.params = {{ lmaID: '{LMA_ID}' }};
    twenty = t.createElement(a);
    two = t.getElementsByTagName(a)[0];
    twenty.async = 1;
    twenty.src = y;
    two.parentNode.insertBefore(twenty, two);
  }})(window, document, 'script', 'https://lma.stay22.com/letmeallez.js');
</script>
{END}
"""
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)


def main() -> None:
    write = "--write" in sys.argv
    added = removed = 0
    for root in ROOTS:
        for f in root.rglob("*.html"):
            rel = f.relative_to(root).as_posix()
            html = f.read_text(encoding="utf-8")
            new = BLOCK_RE.sub("", html)
            if rel in PAGES:
                new = new.replace("</body>", BLOCK + "</body>", 1)
            if new != html:
                if BEGIN in new:
                    added += 1
                else:
                    removed += 1
                if write:
                    f.write_text(new, encoding="utf-8")
    print(f"LetMeAllez: {'wrote' if write else 'would write'} {added} page(s), removed from {removed}")


if __name__ == "__main__":
    main()
