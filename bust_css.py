#!/usr/bin/env python3
"""
bust_css.py — stamp style-v2.css links with a content hash.

GitHub Pages serves the stylesheet with `cache-control: max-age=600`, so after
a deploy a returning visitor can hold a stale CSS for up to ten minutes while
already receiving the new HTML. On 2026-09-13 that shipped a visibly broken
nav (new markup, old CSS). Appending ?v=<hash of the file> makes any CSS change
a new URL, so the browser fetches it immediately.

Idempotent: an existing ?v=… is replaced, so it is safe to re-run. audit_site.py
already strips the query when resolving local links.

  python bust_css.py            # rewrites site/ + docs/
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent
STYLESHEET = "style-v2.css"
# href="…style-v2.css" with an optional existing ?v=… to replace
HREF_RE = re.compile(r'(href=["\'][^"\']*' + re.escape(STYLESHEET) + r')(\?v=[^"\']*)?(["\'])')


def main() -> None:
    css = REPO / "site" / STYLESHEET
    digest = hashlib.sha1(css.read_bytes()).hexdigest()[:8]
    stamp = f"?v={digest}"

    changed = 0
    for base_name in ("site", "docs"):
        base = REPO / base_name
        if not base.exists():
            continue
        for path in base.rglob("*.html"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            new = HREF_RE.sub(lambda m: m.group(1) + stamp + m.group(3), text)
            if new != text:
                path.write_text(new, encoding="utf-8")
                changed += 1
    print(f"  css cache-buster {stamp} applied to {changed} file(s)")


if __name__ == "__main__":
    main()
