#!/usr/bin/env python3
"""
add_travelpayouts_drive.py

Injects the Travelpayouts Drive auto-link-optimization script before
</head> on every public HTML page (articles, country profiles, city
guides, home page, legal pages). Drive automatically converts plain
references to supported travel brands (Booking.com, Skyscanner,
GetYourGuide, etc.) into affiliated links via your Travelpayouts
account — so any future article that mentions those brands earns
commissions without us editing the HTML each time.

Idempotent — running twice does not insert duplicates.
Usage:
  python add_travelpayouts_drive.py            # dry run
  python add_travelpayouts_drive.py --write    # apply
"""

from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKIP_NAMES = {"googlee46af4b13b14f75e.html"}  # GSC verification stub

MARKER_BEGIN = "<!-- BEGIN Travelpayouts Drive (managed by add_travelpayouts_drive.py) -->"
MARKER_END = "<!-- END Travelpayouts Drive -->"

# Exactly the snippet Travelpayouts hands out, preserving the attributes
# that tell WP caching plugins to leave it alone (no harm on a static
# site, and useful if anyone re-platforms later).
TAG = (
    '<script nowprocket data-noptimize="1" data-cfasync="false" '
    'data-wpfc-render="false" seraph-accel-crit="1" data-no-defer="1">\n'
    '    (function () {\n'
    '      var script = document.createElement("script");\n'
    '      script.async = 1;\n'
    "      script.src = 'https://tpembars.com/NTQzNzE5.js?t=543719';\n"
    "      document.head.appendChild(script);\n"
    "    })();\n"
    "  </script>"
)

BLOCK = f"  {MARKER_BEGIN}\n  {TAG}\n  {MARKER_END}\n"


def inject(html: str) -> tuple[str, bool]:
    if MARKER_BEGIN in html:
        return html, False
    needle = "</head>"
    idx = html.rfind(needle)
    if idx == -1:
        return html, False
    return html[:idx] + BLOCK + html[idx:], True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="apply (otherwise dry run)")
    args = parser.parse_args()

    counts = {"changed": 0, "noop": 0, "no_head": 0}
    for base in ("site", "docs"):
        root = REPO_ROOT / base
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.html")):
            if path.name in SKIP_NAMES:
                continue
            text = path.read_text(encoding="utf-8")
            new, changed = inject(text)
            if not changed:
                counts["noop" if MARKER_BEGIN in text else "no_head"] += 1
                continue
            if args.write:
                path.write_text(new, encoding="utf-8")
            counts["changed"] += 1
            print(f"  {'wrote' if args.write else 'would write'} {path.relative_to(REPO_ROOT)}")

    print()
    print(f"changed: {counts['changed']}   noop (already had it): {counts['noop']}   skipped (no </head>): {counts['no_head']}")
    if not args.write and counts["changed"]:
        print("(dry run — pass --write to apply)")


if __name__ == "__main__":
    main()
