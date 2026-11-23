"""Give every sitemap entry that lacks one a true <lastmod>: the date the page was first committed.

Why (weekly PDCA 2026-11-23): 197 of 398 sitemap entries had no lastmod, including every page published
since mid-October. Search Console's URL Inspection said "URL is unknown to Google" for the Disneyland
Paris ticket page three weeks after launch, though Google had downloaded the sitemap the day before.
Google reads lastmod only when it is consistently accurate, so we fill it from git and never invent a date.
We use the publish date (first commit), not the last commit: the build pipeline rewrites every page on
every run, so "last commit" would stamp all 398 pages with this week and Google would learn to ignore it.
Entries that already carry a lastmod are left alone; bump one by hand when a page is really rewritten.

Run at the end of ops/pipeline.sh (after every script that adds sitemap entries). Writes site/ and docs/.
A page not yet committed gets today's date (it is about to be published).
"""
from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = "https://gentlyyonder.com/"
ENTRY = re.compile(r"<url>\s*<loc>(?P<loc>[^<]+)</loc>(?P<rest>.*?)</url>", re.S)


def git_dates() -> dict[str, str]:
    """Date (YYYY-MM-DD) each file under site/ was added, one git call."""
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=@%cs", "--name-only", "--", "site"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout
    dates: dict[str, str] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("@"):
            current = line[1:]
        elif line:
            dates[line] = current      # log runs newest first: the last write is the first add
    return dates


def rel_path(loc: str) -> str:
    rel = loc[len(BASE):] if loc.startswith(BASE) else loc
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    return "site/" + rel


def fix(text: str, dates: dict[str, str]) -> tuple[str, int]:
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        if "<lastmod>" in m["rest"]:
            return m[0]
        rel = rel_path(m["loc"])
        if not (REPO / rel).exists():
            return m[0]
        when = dates.get(rel, date.today().isoformat())
        rest = f"\n    <lastmod>{when}</lastmod>" + m["rest"]
        changed += 1
        return f"<url>\n    <loc>{m['loc']}</loc>{rest}</url>"

    return ENTRY.sub(repl, text), changed


def main() -> None:
    dates = git_dates()
    for root in ("site", "docs"):
        p = REPO / root / "sitemap.xml"
        new, n = fix(p.read_text(encoding="utf-8"), dates)
        p.write_text(new, encoding="utf-8")
        print(f"{root}/sitemap.xml: lastmod set on {n} entries")


if __name__ == "__main__":
    main()
