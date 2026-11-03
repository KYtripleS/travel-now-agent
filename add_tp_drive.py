"""Travelpayouts Drive on the pages that may carry affiliate links (the same rule as Stay22's script:
content_classes.py "eligible" only; never history, trust, About or policy pages), except the hotel
guides, which stay with Stay22 alone.

Drive's own settings live in the Travelpayouts account (Drive > Advanced settings), not here. Agreed
settings (2026-11-03): switch links ON but not from other networks (keeps Awin) and with the hotel
brands unticked (hotels stay with Stay22); keyword linking and recommendations ON only after a test;
smart previews ON; targeted offers OFF.

The snippet is pasted, unchanged, from Drive > Manual installation into data/tp_drive_snippet.html
(it is public: it ships in every page that runs it).

usage: python add_tp_drive.py           # dry run
       python add_tp_drive.py --write   # apply to site/ and docs/
       python add_tp_drive.py --remove  # take it off every page
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
ROOTS = (REPO / "site", REPO / "docs")
SNIPPET = REPO / "data" / "tp_drive_snippet.html"
SKIP = {"404.html", "ready-score-pro-thanks.html", "googlee46af4b13b14f75e.html"}
BEGIN = "<!-- BEGIN Travelpayouts Drive (managed by add_tp_drive.py) -->"
END = "<!-- END Travelpayouts Drive -->"
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)


def wanted(rel: str, classes: dict[str, str]) -> bool:
    if rel in SKIP or rel.startswith(("countries/", "cities/", "go/")):
        return False
    # hotel guides stay with Stay22: every hotel link there is checked by hand, and keyword
    # linking could send a hotel name to the wrong property (the HOSHINOYA lesson)
    if Path(rel).name.startswith(("where-to-stay-", "where-to-stay-for-")) or rel.startswith("stay/"):
        return False
    return classes.get(rel, "eligible") == "eligible"


def main() -> None:
    import content_classes
    classes = content_classes.load()
    write, remove = "--write" in sys.argv, "--remove" in sys.argv
    if not remove and not SNIPPET.exists():
        sys.exit(f"missing {SNIPPET.relative_to(REPO)}: paste Drive's manual-installation snippet there first")
    block = "" if remove else f"{BEGIN}\n{SNIPPET.read_text(encoding='utf-8').strip()}\n{END}\n"
    added = removed = 0
    for root in ROOTS:
        for p in sorted(root.rglob("*.html")):
            rel = p.relative_to(root).as_posix()
            html = p.read_text(encoding="utf-8")
            new = BLOCK_RE.sub("", html)
            if block and wanted(rel, classes) and "</head>" in new:
                new = new.replace("</head>", block + "</head>", 1)
            if new != html:
                added += BEGIN in new
                removed += BEGIN in html and BEGIN not in new
                if write or remove:
                    p.write_text(new, encoding="utf-8")
    print(f"Drive: {'wrote' if write or remove else 'would write'} {added} page(s), removed from {removed}")


if __name__ == "__main__":
    main()
