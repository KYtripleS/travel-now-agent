"""Register a finished ticket comparison (prompts/ticket_brief.md) in the registries a ticket page needs:
site_taxonomy (Booking & tours), data/content_classes.csv, llms.txt (site + docs, "Ticket comparisons")
and the facts ledger. Idempotent: skips a registry that already names the slug.

The verdict box (add_aeo.V), the pointer from the stay guide (add_aeo.STAY_POINTERS) and any why-now
line (data/why_now.json) are written by hand: they are editorial calls.

usage: .venv/bin/python ops/register_ticket.py <slug> <country-facts-file>
e.g.   .venv/bin/python ops/register_ticket.py where-to-buy-tokyo-disney-resort-tickets japan
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
slug, facts_file = sys.argv[1:3]
R = json.loads((REPO / "content_drafts" / "tickets" / f"{slug}.json").read_text())
art = f"articles/{slug}.html"
assert (REPO / "site" / art).exists(), f"publish {slug} first"

# 1. taxonomy
p = REPO / "site_taxonomy.py"; t = p.read_text()
if f'"{slug}"' not in t:
    anchor = "    # 2026-10-31 ticket comparisons\n"
    assert anchor in t
    p.write_text(t.replace(anchor, anchor + f'    "{slug}": "Booking & tours",\n', 1)); print("  + site_taxonomy")

# 2. content classes
p = REPO / "data" / "content_classes.csv"; b = p.read_bytes()   # CRLF file: append bytes, keep endings
if art.encode() not in b:
    p.write_bytes(b + f"{art},eligible,Booking & tours,\r\n".encode()); print("  + content_classes")

# 3. llms.txt: one section for every ticket comparison, above the hotel guides
line = R["llms_line"].strip()
for root in ("site", "docs"):
    p = REPO / root / "llms.txt"; t = p.read_text()
    if f"/{art})" in t:
        continue
    head = "## Ticket comparisons (where to buy)\n"
    if head not in t:
        t = t.replace("## Where to stay (hotel guides)\n", head + "\n## Where to stay (hotel guides)\n", 1)
    i = t.index(head) + len(head); j = t.index("\n\n", i - 1)
    t = t[:j] + "\n" + line + t[j:] if t[i:j].strip() else t[:i] + line + "\n" + t[i:]
    p.write_text(t); print(f"  + {root}/llms.txt")

# 4. facts ledger (new ids appended; an id already in the ledger gets this page's usage)
KINDS = {"official", "operator", "news", "secondary"}
fp = REPO / "data" / "facts" / f"{facts_file}.json"; d = json.loads(fp.read_text())
have = {f["id"]: f for f in d["facts"]}; new = []
for f in R["facts"]:
    for s in f.get("sources", []):
        s["kind"] = s.get("kind") if s.get("kind") in KINDS else "secondary"
    if f["id"] in have:
        have[f["id"]].setdefault("used_in", {}).update(f.get("used_in", {})); continue
    for x in f.get("used_in", {}).values():
        x[:] = [q.replace("...", "").strip() for q in x]
    new.append(f)
d["facts"] += new
fp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"); print(f"  + {len(new)} facts -> {fp.name}")
