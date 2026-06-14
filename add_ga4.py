#!/usr/bin/env python3
"""
add_ga4.py — Inject GA4 (Google Analytics 4) tracking code into every HTML page.

Usage:
    python add_ga4.py G-XXXXXXXXXX           # add or update the GA4 snippet
    python add_ga4.py --remove                # strip the GA4 snippet out
    python add_ga4.py --check                 # report which files have it

The snippet is wrapped in distinctive comment markers so we can find/update/remove
it idempotently — running the script twice does NOT duplicate the snippet.
"""

from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent
SCAN_DIRS = [ROOT / "site", ROOT / "docs"]

START = "<!-- BEGIN GA4 (managed by add_ga4.py) -->"
END = "<!-- END GA4 -->"
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\s*", re.DOTALL)


def snippet(measurement_id: str) -> str:
    return f"""{START}
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{measurement_id}', {{
    anonymize_ip: true
  }});
</script>
{END}
"""


def html_files():
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.html"):
            # skip Google Search Console verification stub
            if p.name.startswith("google") and "verif" in p.read_text(errors="ignore")[:200].lower():
                continue
            if p.name.startswith("google") and len(p.name) > 15:  # googleXXXXX.html
                continue
            yield p


def inject(measurement_id: str):
    snip = snippet(measurement_id)
    changed = added = updated = 0
    for p in html_files():
        text = p.read_text()
        if START in text:
            new_text = BLOCK_RE.sub(snip, text)
            if new_text != text:
                p.write_text(new_text)
                updated += 1
                changed += 1
        else:
            # insert right before </head>
            if "</head>" not in text:
                print(f"  ⚠️  {p.relative_to(ROOT)} — no </head> found, skipped")
                continue
            new_text = text.replace("</head>", f"  {snip}</head>", 1)
            p.write_text(new_text)
            added += 1
            changed += 1
    print(f"✅ GA4 snippet processed: {added} added, {updated} updated, {changed} files changed")


def remove():
    changed = 0
    for p in html_files():
        text = p.read_text()
        if START in text:
            new_text = BLOCK_RE.sub("", text)
            p.write_text(new_text)
            changed += 1
    print(f"✅ GA4 snippet removed from {changed} files")


def check():
    have = miss = 0
    for p in html_files():
        text = p.read_text()
        if START in text:
            have += 1
            # extract ID
            m = re.search(r"id=(G-[A-Z0-9]+)", text)
            mid = m.group(1) if m else "?"
            print(f"  ✅ {p.relative_to(ROOT)} ({mid})")
        else:
            miss += 1
            print(f"  ❌ {p.relative_to(ROOT)} (missing)")
    print(f"\nTotal: {have} with GA4, {miss} without")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    arg = sys.argv[1]
    if arg == "--remove":
        remove()
    elif arg == "--check":
        check()
    elif re.match(r"^G-[A-Z0-9]+$", arg):
        inject(arg)
    else:
        print(f"Error: '{arg}' is not a valid GA4 Measurement ID (must start with G-)")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
