#!/usr/bin/env python3
"""
bust_assets.py — stamp CSS and JS links with a content hash.

GitHub Pages serves static assets with `cache-control: max-age=600`, so after a
deploy a returning visitor can hold a stale asset for up to ten minutes while
already receiving the new HTML. That shipped two visible bugs on 2026-09-13:
new nav markup with old CSS (a giant black search icon), then new CSS with an
old gy-search.js (the tours widget kept its clipped height).

Appending ?v=<hash of that file> makes any change a new URL, so browsers fetch
it immediately. Each asset gets its own hash, so touching one file does not
invalidate the others.

Idempotent — an existing ?v=… is replaced, so it is safe to re-run.
audit_site.py already strips the query when resolving local links.

RUN THIS LAST. add_global_nav.py rewrites the <script src="…gy-search.js">
tag from its own template, so running it afterwards would drop the stamp.

  python bust_assets.py          # rewrites site/ + docs/
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent

# asset path relative to the site root -> attribute it appears in
ASSETS = [
    ("style-v2.css", "href"),
    ("js/gy-search.js", "src"),
    ("js/gy-reveal.js", "src"),
    ("js/email-popup.js", "src"),
]


def main() -> None:
    stamps: dict[str, str] = {}
    for rel, _ in ASSETS:
        f = REPO / "site" / rel
        if f.exists():
            stamps[rel] = hashlib.sha1(f.read_bytes()).hexdigest()[:8]

    patterns = []
    for rel, attr in ASSETS:
        if rel not in stamps:
            continue
        name = rel.split("/")[-1]
        # attr="<anything>/name" with an optional existing ?v=… to replace
        patterns.append((
            re.compile(rf'({attr}=["\'][^"\']*{re.escape(name)})(\?v=[^"\']*)?(["\'])'),
            stamps[rel],
        ))

    changed = 0
    for base_name in ("site", "docs"):
        base = REPO / base_name
        if not base.exists():
            continue
        for path in base.rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            new = text
            for rx, stamp in patterns:
                new = rx.sub(lambda m, s=stamp: f"{m.group(1)}?v={s}{m.group(3)}", new)
            if new != text:
                path.write_text(new, encoding="utf-8")
                changed += 1

    for rel, stamp in stamps.items():
        print(f"  {rel:<22} ?v={stamp}")
    print(f"  stamped {changed} file(s)")


if __name__ == "__main__":
    main()
