"""Swap partner listing URLs in a draft for Travelpayouts short links (2026-11-21).

Finds every Viator, KKday, Tiqets, GetYourGuide and Klook listing URL in
content_drafts/<slug>.final.md, written as a Markdown link target or an href, creates the short links
that are not cached yet (ops/tp_deeplinks.create, cache data/tp_deeplinks.json) and replaces them.

usage: .venv/bin/python ops/tpconv.py <slug>
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "ops"))
import tp_deeplinks as T  # noqa: E402

slug = sys.argv[1]
p = REPO / "content_drafts" / f"{slug}.final.md"
s = p.read_text(encoding="utf-8")
R = r'https://(?:www\.)?(?:viator|kkday|tiqets|getyourguide|klook)\.com[^)\s"]*'
urls = sorted(set(re.findall(r'\]\((' + R + r')\)', s)) | set(re.findall(r'href="(' + R + r')"', s)))
cache = json.loads(T.CACHE.read_text()) if T.CACHE.exists() else {}
need = [u for u in urls if u not in cache]
if need:
    cache.update(T.create(need))
    T.CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
n = 0
for u in urls:
    if u in cache:
        s = s.replace(f"]({u})", f"]({cache[u]})").replace(f'href="{u}"', f'href="{cache[u]}"')
        n += 1
p.write_text(s, encoding="utf-8")
print(slug, "converted", n, "of", len(urls))
if n < len(urls):
    sys.exit(f"{len(urls) - n} link(s) not converted")
