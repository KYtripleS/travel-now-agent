"""Weekly freshness run: keeps the money blocks current without a person, and lists what needs one.

1. eSIM prices: refresh Airalo's from its site (ops/esim_prices.py); flag Saily's when stale.
2. Facts due for a recheck in the next 14 days (facts.py --due).
3. Event and season guides whose dates have passed (they need next year's edition).
4. Stay22 bookings in the last 7 days (ops/stay22_report.py).
5. With --publish: when the only change is refreshed prices, rebuild, run every check and, if all
   pass, commit and push. Anything else is left for the editor.

The report goes to ops/state/weekly-<date>.md (gitignored).
usage: .venv/bin/python ops/weekly.py [--publish]
"""
import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / ".venv" / "bin" / "python")
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july",
                                       "august", "september", "october", "november", "december"], 1)}


def run(*args: str, check: bool = False) -> tuple[int, str]:
    p = subprocess.run(args, cwd=REPO, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"{' '.join(args)} failed:\n{p.stdout[-2000:]}{p.stderr[-2000:]}")
    return p.returncode, (p.stdout + p.stderr).strip()


def past_events(today: date) -> list[str]:
    """Event/season guides whose title year is over: a '2026' event once 2026 has ended,
    a '2026/27' season once its April has passed."""
    out = []
    for f in sorted((REPO / "site" / "articles").glob("where-to-stay-*.html")):
        m = re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8", errors="ignore"), re.S)
        title = m.group(1) if m else ""
        season = re.search(r"\b(20\d\d)/(\d\d)\b", title)
        single = re.search(r"\b(20\d\d)\b", title)
        if season and today > date(2000 + int(season.group(2)), 4, 30):
            out.append(f"{f.stem}: season {season.group(0)} is over")
        elif not season and single and any(k in title for k in ("New Year", "Christmas", "Festival", "Hogmanay",
                                                                 "Carnival", "Cherry Blossom", "Autumn")):
            if today.year > int(single.group(1)) + (1 if "New Year" in title or "Hogmanay" in title else 0):
                out.append(f"{f.stem}: '{single.group(1)}' event has passed")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    today = date.today()
    lines = [f"# Weekly freshness run, {today}", ""]

    code, out = run(PY, "ops/esim_prices.py")
    lines += ["## eSIM prices", "```", out[-1500:], "```"]
    _, diff = run("git", "diff", "--stat", "--", "data/esim_plans.json")
    prices_changed = bool(diff.strip())
    lines.append(f"Airalo prices changed: {'yes' if prices_changed else 'no'}")

    _, due = run(PY, "facts.py", "--due")
    lines += ["", "## Facts due for a recheck (next 14 days)", "```", due[-3000:] or "none", "```"]

    events = past_events(today)
    lines += ["", "## Event and season guides that need next year's edition"] + ([f"- {e}" for e in events] or ["- none"])

    code, s22 = run(PY, "ops/stay22_report.py", "--days", "7")
    lines += ["", "## Stay22 bookings, last 7 days", "```", s22[-1500:], "```"]

    if args.publish and prices_changed:
        _, status = run("git", "status", "--porcelain")
        others = [l for l in status.splitlines() if not l.endswith("data/esim_plans.json")]
        if others:
            lines.append("\nNot published: the tree had other changes.")
        else:
            try:
                run("zsh", "ops/pipeline.sh", check=True)
                for cmd in ([PY, "audit_site.py"], [PY, "facts.py"], [PY, "test_monetization.py"]):
                    code, out = run(*cmd)
                    if code or "FAIL" in out:
                        raise RuntimeError(f"{cmd[-1]} did not pass:\n{out[-1500:]}")
                run("git", "add", "-A", check=True)
                run("git", "commit", "-q", "-m", f"Refresh Airalo eSIM prices ({today}, weekly run)\n\n"
                    "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>", check=True)
                run("git", "push", "-q", "origin", "main", check=True)
                run(PY, "indexnow.py", "--since", "HEAD~1")
                lines.append("\nPublished the refreshed prices.")
            except RuntimeError as e:
                run("git", "checkout", "--", ".")
                lines.append(f"\nNot published, changes discarded: {e}")

    report = REPO / "ops" / "state" / f"weekly-{today}.md"
    report.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
