"""Bylines: give each article its writer (data/authors.json) and a round portrait left of "By ...".

Writers are pen names, disclosed on editors.html. The writer follows the article's beat: an event
or season slug first, then a history/tax slug, then the content_classes.csv label, else Casey.
Only the visible byline changes; the structured-data author stays the publication. Idempotent.

usage: .venv/bin/python ops/authors.py [--write]
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE, DOCS = REPO / "site", REPO / "docs"
A = json.loads((REPO / "data/authors.json").read_text())["authors"]
BY_ID = {a["id"]: a for a in A}
LABELS = {r["path"]: r["label"] for r in csv.DictReader(open(REPO / "data/content_classes.csv"))}
BYLINE = re.compile(r'<p class="article-byline">.*?</p>', re.S)


def writer_for(rel: str) -> dict:
    if rel.startswith("countries/"):               # the layered country profiles: history and culture
        return BY_ID["margaret"]
    if rel.startswith("cities/"):                  # city and neighbourhood guides
        return BY_ID["mina"]
    slug = Path(rel).stem
    for a in A:                                    # slug beats win: an event guide is an event guide
        pat = a["beats"].get("slug")
        if pat and re.search(pat, slug):
            return a
    label = LABELS.get(rel, "")
    for a in A:
        if label in a["beats"].get("labels", []):
            return a
    return BY_ID["casey"]


def byline(a: dict, src: Path) -> str:
    up = os.path.relpath(SITE, src.parent).replace(os.sep, "/")
    up = "" if up == "." else up + "/"
    title = "Gently Yonder editor" if a["id"] == "casey" else "Gently Yonder writer"
    return (f'<p class="article-byline"><img alt="" class="gy-byline-photo" height="40" '
            f'src="{up}{a["photo"]}" width="40"/><span>By <a href="{up}editors.html#{a["id"]}">{a["name"]}</a>, '
            f'{title}</span></p>')


def main() -> None:
    write = "--write" in sys.argv
    changed, count = 0, {}
    pages = (sorted((SITE / "articles").glob("*.html")) + sorted((SITE / "cities").glob("*/*.html"))
             + sorted((SITE / "countries").glob("*/index.html")))
    for src in pages:
        rel = src.relative_to(SITE).as_posix()
        html = src.read_text(encoding="utf-8")
        if 'class="article-byline"' not in html:
            continue
        a = writer_for(rel)
        count[a["id"]] = count.get(a["id"], 0) + 1
        new = BYLINE.sub(lambda m: byline(a, src), html, count=1)
        if new != html:
            changed += 1
            if write:
                src.write_text(new, encoding="utf-8")
                (DOCS / rel).write_text(new, encoding="utf-8")
    print(f"bylines changed: {changed}   by writer: {count}")
    if not write:
        print("  (dry run: pass --write)")


if __name__ == "__main__":
    main()
