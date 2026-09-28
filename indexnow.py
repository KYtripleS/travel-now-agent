#!/usr/bin/env python3
"""Tell Bing (and the other IndexNow engines) which pages just changed.

About a third of the site's real readers arrive from ChatGPT, whose search leans on
Bing's index. Bing finds a new or rewritten page on its own schedule, sometimes
weeks later; IndexNow tells it the same day. One POST reaches every participating
engine (Bing, Yandex, Seznam, Naver). Google does not take part.

The key file site/<KEY>.txt proves we own the domain. It must be live before a
ping counts, so run this after the push has deployed, never before.

Usage:
    python indexnow.py --since HEAD~1          # pages changed by the last commit
    python indexnow.py --since 3ab01ed --dry   # show what would be sent
    python indexnow.py articles/where-to-stay-in-tokyo.html ...
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent
SITE = REPO / "site"
HOST = "gentlyyonder.com"
KEY = "5e1417ad44e95d06205517a30c7ac6a2"
ENDPOINT = "https://api.indexnow.org/indexnow"


def url_for(rel: str) -> str:
    rel = rel.removeprefix("site/")
    if rel == "index.html":
        return f"https://{HOST}/"
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    return f"https://{HOST}/{rel}"


def sitemap_urls() -> set[str]:
    return set(re.findall(r"<loc>([^<]+)</loc>", (SITE / "sitemap.xml").read_text(encoding="utf-8")))


STAMP = re.compile(r"\?v=[0-9a-f]+")


def _real_change(ref: str, path: str) -> bool:
    """False when the only edits are bust_assets' ?v= stamps: a CSS change restamps
    every page, and pinging 190 unchanged pages would teach Bing to ignore us."""
    diff = subprocess.run(["git", "diff", "-U0", ref, "HEAD", "--", path], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout.splitlines()
    minus = [STAMP.sub("", l[1:]) for l in diff if l.startswith("-") and not l.startswith("---")]
    plus = [STAMP.sub("", l[1:]) for l in diff if l.startswith("+") and not l.startswith("+++")]
    return sorted(minus) != sorted(plus)


def changed_since(ref: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", ref, "HEAD", "--", "site"],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout.split()
    return [p for p in out if p.endswith(".html") and _real_change(ref, p)]


def key_is_live() -> bool:
    try:
        with urllib.request.urlopen(f"https://{HOST}/{KEY}.txt", timeout=15) as r:
            return r.read().decode().strip() == KEY
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="*", help="site-relative paths, e.g. articles/x.html")
    ap.add_argument("--since", help="git ref: send every page changed since it")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    rels = list(args.pages) + (changed_since(args.since) if args.since else [])
    listed = sitemap_urls()
    # only pages the sitemap lists: no 404s, stubs or verification files
    urls = sorted({u for u in map(url_for, rels) if u in listed})
    if not urls:
        sys.exit("nothing to send (no changed page is in sitemap.xml)")
    print(f"{len(urls)} URL(s):")
    for u in urls:
        print("  ", u)
    if args.dry:
        return
    if not key_is_live():
        sys.exit(f"key file https://{HOST}/{KEY}.txt is not live yet; push, wait for the deploy, retry")
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("IndexNow:", r.status, "(200/202 = accepted)")
    except urllib.error.HTTPError as e:
        sys.exit(f"IndexNow refused: {e.code} {e.read().decode()[:200]}")


if __name__ == "__main__":
    main()
