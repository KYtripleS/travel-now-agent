#!/usr/bin/env python3
"""
add_privacy_footer.py — Inject a Privacy link into the standard footer of every
page that currently has the Editorial Guidelines footer link. Idempotent.
"""

from __future__ import annotations
import re
from pathlib import Path
import re as _re

ROOT = Path(__file__).parent
SCAN_DIRS = [ROOT / "site", ROOT / "docs"]

# Handle 3 relative-path variants: root, /articles or /cities (1-up), /countries/X (2-up)
PATTERNS = [
    # (relative prefix, search needle, replacement needle)
    ("", '<a href="editorial.html">Editorial Guidelines</a> ·\n      <a href="https://x.com/TripWorldAdvice">',
         '<a href="editorial.html">Editorial Guidelines</a> ·\n      <a href="privacy.html">Privacy</a> ·\n      <a href="https://x.com/TripWorldAdvice">'),
    ("../", '<a href="../editorial.html">Editorial Guidelines</a> ·\n      <a href="https://x.com/TripWorldAdvice">',
            '<a href="../editorial.html">Editorial Guidelines</a> ·\n      <a href="../privacy.html">Privacy</a> ·\n      <a href="https://x.com/TripWorldAdvice">'),
    ("../../", '<a href="../../editorial.html">Editorial Guidelines</a> ·\n      <a href="https://x.com/TripWorldAdvice">',
               '<a href="../../editorial.html">Editorial Guidelines</a> ·\n      <a href="../../privacy.html">Privacy</a> ·\n      <a href="https://x.com/TripWorldAdvice">'),
]


# Article-style footer (Disclosure text) — append a nav line after the disclosure
DISCLOSURE_OLD = "Always check the latest official guidance from your airport, airline, or transport security\n      authority before your trip.\n    </p>\n  </footer>"
DISCLOSURE_NEW_PREFIX = "Always check the latest official guidance from your airport, airline, or transport security\n      authority before your trip.\n    </p>\n    <p class=\"footer-nav\">\n      <a href=\""
# Suffix differs per relative-path depth (1-up: ../ , 2-up: ../../)

_FOOTER_RE = re.compile(
    r"(<footer>\s*<p>\s*Disclosure:.*?</p>)\s*(</footer>)",
    re.DOTALL,
)


def patch_article_footer(text: str, prefix: str) -> tuple[str, bool]:
    if "footer-nav" in text:
        return text, False
    nav = (
        f'\n    <p class="footer-nav">\n'
        f'      <a href="{prefix}about.html">About</a> · '
        f'<a href="{prefix}editorial.html">Editorial Guidelines</a> · '
        f'<a href="{prefix}privacy.html">Privacy</a>\n'
        f'    </p>\n  '
    )
    new_text, n = _FOOTER_RE.subn(r"\1" + nav + r"\2", text, count=1)
    return new_text, n > 0


def main():
    changed = skipped_already = skipped_no_match = 0
    article_added = 0
    for d in SCAN_DIRS:
        for p in d.rglob("*.html"):
            text = p.read_text()
            if 'privacy.html">Privacy</a>' in text:
                skipped_already += 1
                continue
            matched = False
            for _, old, new in PATTERNS:
                if old in text:
                    p.write_text(text.replace(old, new))
                    changed += 1
                    print(f"  ✅ {p.relative_to(ROOT)}")
                    matched = True
                    break
            if not matched:
                # Try article-style footer
                rel = p.relative_to(d)
                depth = len(rel.parts) - 1
                prefix = "../" * depth
                new_text, did_change = patch_article_footer(text, prefix)
                if did_change:
                    p.write_text(new_text)
                    article_added += 1
                    print(f"  ✅ (article) {p.relative_to(ROOT)}")
                else:
                    skipped_no_match += 1
    print(f"\nMain footer added: {changed}, article footer added: {article_added}, already: {skipped_already}, no footer: {skipped_no_match}")


if __name__ == "__main__":
    main()
