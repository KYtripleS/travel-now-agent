#!/usr/bin/env python3
"""
add_reveal_script.py

Inject the scroll-reveal script (js/gy-reveal.js) into every public HTML
page, right before </body>, with a depth-correct relative path. Idempotent
via BEGIN/END markers (same pattern as add_global_nav.py / add_email_popup.py).

Usage:
  python add_reveal_script.py          # inject / update everywhere
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent
ROOTS = [REPO / "site", REPO / "docs"]
MARK_BEGIN = "<!-- BEGIN gy-reveal (managed by add_reveal_script.py) -->"
MARK_END = "<!-- END gy-reveal -->"


def block(rel_prefix: str) -> str:
    return (f"{MARK_BEGIN}\n"
            f'<script defer src="{rel_prefix}js/gy-reveal.js"></script>\n'
            f"{MARK_END}\n")


def main() -> None:
    changed = 0
    for root in ROOTS:
        for p in root.rglob("*.html"):
            rel = p.relative_to(root)
            depth = len(rel.parts) - 1
            prefix = "../" * depth
            html = p.read_text(encoding="utf-8")
            if "</body>" not in html:
                continue
            snippet = block(prefix)
            if MARK_BEGIN in html:
                start = html.index(MARK_BEGIN)
                end = html.index(MARK_END) + len(MARK_END)
                # include trailing newline if present
                tail = html[end:end + 1]
                if tail == "\n":
                    end += 1
                html = html[:start] + snippet + html[end:]
            else:
                html = html.replace("</body>", snippet + "</body>", 1)
            p.write_text(html, encoding="utf-8")
            changed += 1
    print(f"  injected/updated gy-reveal on {changed} pages")


if __name__ == "__main__":
    main()
