#!/usr/bin/env python3
"""
enhance_article_citations.py

For research-heavy Travel Now articles, attach a Nikkei-style footnote
to the first mention of each researcher and append a "Researcher notes"
section listing affiliations, dates, and what they're known for.

Idempotent — running twice does not double up footnotes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

REPO_ROOT = Path(__file__).resolve().parent
SITE_DIR  = REPO_ROOT / "site"
DOCS_DIR  = REPO_ROOT / "docs"


# slug → ordered list of (researcher surname, bio sentence)
RESEARCHERS: dict[str, list[tuple[str, str]]] = {
    "what-counts-as-rude": [
        ("Goffman",
         "Erving Goffman (1922–1982), Canadian-American sociologist at the "
         "University of Pennsylvania, known for dramaturgical analysis in "
         "<em>The Presentation of Self in Everyday Life</em> (1956) and for "
         "introducing the social-interactionist concept of 'face'."),
        ("Hofstede",
         "Geert Hofstede (1928–2020), Dutch social psychologist at "
         "Maastricht University; originator of the cultural-dimensions "
         "theory in <em>Culture's Consequences</em> (1980), now extended "
         "to six dimensions."),
        ("Brown",
         "Penelope Brown, linguistic anthropologist at the Max Planck "
         "Institute for Psycholinguistics in the Netherlands; co-author "
         "with Stephen Levinson of <em>Politeness: Some Universals in "
         "Language Usage</em> (1987)."),
        ("Levinson",
         "Stephen C. Levinson, cognitive scientist and director emeritus "
         "of the Max Planck Institute for Psycholinguistics, where he led "
         "the Language and Cognition Department."),
        ("Wierzbicka",
         "Anna Wierzbicka, Polish-Australian linguist at Australian "
         "National University; developer of the Natural Semantic "
         "Metalanguage (NSM) framework for cross-cultural semantics."),
    ],
    "untranslatable-words": [
        ("Wierzbicka",
         "Anna Wierzbicka, Polish-Australian linguist at Australian "
         "National University; developer of the Natural Semantic "
         "Metalanguage (NSM) framework for cross-cultural semantics."),
        ("Boroditsky",
         "Lera Boroditsky, American cognitive scientist at UC San Diego; "
         "her research examines how language shapes thought across colour, "
         "time, and spatial cognition."),
        ("Sapir",
         "Edward Sapir (1884–1939), American linguist and anthropologist "
         "at Yale University; foundational figure in descriptive "
         "linguistics and the linguistic-relativity hypothesis."),
        ("Whorf",
         "Benjamin Lee Whorf (1897–1941), American linguist at Yale "
         "University; co-developer with Sapir of the linguistic-relativity "
         "hypothesis through his work on Hopi and other languages."),
    ],
}


SLUG_TO_PATH = {
    "what-counts-as-rude":  Path("articles/what-counts-as-rude.html"),
    "untranslatable-words": Path("articles/untranslatable-words.html"),
}


SUPERSCRIPTS = ["¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹", "¹⁰"]


def article_body(soup: BeautifulSoup):
    for sel in ("main section.article", "main", "article"):
        el = soup.select_one(sel)
        if el is not None:
            return el
    return soup.body


def insert_footnote_marker(body, surname: str, index: int) -> bool:
    """Add a <sup class="citation-mark"> right after the first occurrence
    of `surname` in the body text. Returns True if a marker was inserted."""
    pattern = re.compile(rf"\b{re.escape(surname)}\b")
    for text_node in list(body.find_all(string=True)):
        if not isinstance(text_node, NavigableString):
            continue
        parent = text_node.parent
        if parent is None:
            continue
        # Skip text inside <sup>, <script>, <style>, etc.
        if parent.name in ("sup", "script", "style", "head"):
            continue
        # Skip if this text is already inside an existing citation block
        if any(p.name == "section" and "researcher-notes" in (p.get("class") or [])
               for p in parent.parents if p.name):
            continue

        match = pattern.search(str(text_node))
        if not match:
            continue

        # Don't double-up: if the next char in the parent is already a sup
        # with the same index id, skip
        next_sib = text_node.next_sibling
        if (next_sib is not None and getattr(next_sib, "name", None) == "sup"
                and next_sib.get("data-cite") == surname):
            return True  # already marked

        before = str(text_node)[: match.end()]
        after = str(text_node)[match.end():]
        new_text_before = NavigableString(before)
        new_text_after = NavigableString(after)

        sup_html = (
            f'<sup class="citation-mark" data-cite="{surname}">'
            f'<a href="#researcher-{surname.lower()}" '
            f'aria-describedby="researcher-{surname.lower()}">'
            f'{SUPERSCRIPTS[index]}</a></sup>'
        )
        sup_tag = BeautifulSoup(sup_html, "html.parser").sup

        text_node.replace_with(new_text_before)
        new_text_before.insert_after(sup_tag)
        sup_tag.insert_after(new_text_after)
        return True
    return False


def build_notes_section(soup: BeautifulSoup, entries: list[tuple[str, str]]) -> "BeautifulSoup":
    section = soup.new_tag("section", **{"class": "researcher-notes", "aria-labelledby": "researcher-notes-heading"})
    h = soup.new_tag("h2", id="researcher-notes-heading")
    h.string = "Researcher notes"
    section.append(h)

    intro = soup.new_tag("p", **{"class": "researcher-notes-intro"})
    intro.string = "Sources for the claims attributed above. Affiliations and dates current at last revision."
    section.append(intro)

    ol = soup.new_tag("ol", **{"class": "researcher-notes-list"})
    for i, (surname, bio) in enumerate(entries):
        li = soup.new_tag("li", id=f"researcher-{surname.lower()}")
        bio_soup = BeautifulSoup(bio, "html.parser")
        for node in list(bio_soup.contents):
            li.append(node)
        ol.append(li)
    section.append(ol)
    return section


def enhance(slug: str) -> int:
    rel = SLUG_TO_PATH[slug]
    site_path = SITE_DIR / rel
    docs_path = DOCS_DIR / rel
    if not site_path.exists():
        print(f"  ! file missing: {site_path}")
        return 0
    entries = RESEARCHERS[slug]

    soup = BeautifulSoup(site_path.read_text(encoding="utf-8"), "html.parser")
    body = article_body(soup)
    if body is None:
        print("  ! no article body")
        return 0

    # Skip if researcher-notes already exists
    if soup.find("section", class_="researcher-notes"):
        print("  already has researcher-notes — skip")
        return 0

    inserted = 0
    for i, (surname, _bio) in enumerate(entries):
        ok = insert_footnote_marker(body, surname, i)
        if ok:
            print(f"  [{SUPERSCRIPTS[i]}] {surname}")
            inserted += 1
        else:
            print(f"  [-] {surname} (not found in body)")

    if inserted == 0:
        return 0

    # Insert "Researcher notes" section immediately before any Sources/FAQ
    # section, or before newsletter-cta, or just before back-link.
    notes = build_notes_section(soup, entries)
    anchor = (
        soup.find("h2", id="sources")
        or soup.find("section", class_="newsletter-cta")
        or soup.find("p", class_="back-link")
    )
    if anchor:
        anchor.insert_before(notes)
    else:
        body.append(notes)

    site_path.write_text(str(soup), encoding="utf-8")
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(site_path.read_text(encoding="utf-8"), encoding="utf-8")
    return inserted


def main() -> None:
    args = sys.argv[1:]
    if args:
        slugs = args
    else:
        slugs = list(SLUG_TO_PATH.keys())
    total = 0
    for slug in slugs:
        if slug not in SLUG_TO_PATH:
            print(f"unknown slug: {slug}")
            continue
        print(f"\n[{slug}]")
        total += enhance(slug)
    print(f"\n— total footnotes inserted: {total} —")


if __name__ == "__main__":
    main()
