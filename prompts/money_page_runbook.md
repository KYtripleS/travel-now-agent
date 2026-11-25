# Runbook: one money page, end to end (2026-11-22)

Used by the daily scheduled run (one page a day, seven a week). The lead editor runs this; a writer agent
drafts. Read CLAUDE.md first. Python is .venv/bin/python.

## 0. Preconditions (stop and log if any fails)
- `git status --porcelain` shows no changes to tracked files, and `pgrep -f "pipeline.sh|add_aeo.py"` finds
  nothing. Another session is working otherwise: write one line to the log and stop. Never stash or discard
  someone else's changes.
- `git pull --ff-only` succeeds.

## 1. Pick
Take the top "todo" row in ops/state/money_backlog.md and mark it "doing <date>". Check
`ls site/articles/<slug>.html` does not exist. If it does, mark the row "done (already existed)" and take the next one.

## 2. Draft (writer agent)
Spawn ONE background agent: subagent_type "general-purpose", model "sonnet". Its prompt:
- the slug, the product and city, the visit date from the backlog row, one adult;
- "First read prompts/ticket_brief.md completely and follow it exactly, including 'Lessons from 21 November
  2026' (load the built-in browser tools with ToolSearch, tabs_create first, tabId on every call, close the tab).";
- a finished example to copy: a tour → where-to-book-tromso-northern-lights-tour, a ticket →
  where-to-buy-empire-state-building-tickets (content_drafts/<slug>.final.md and content_drafts/tickets/<slug>.json);
- "Before pricing, read the venue's own terms/FAQ. If it refuses or voids tickets from unauthorised resellers and
  names no authorised partner, STOP and report. If it names authorised partners, compare only those, and say so
  neutrally (see where-to-buy-shibuya-sky-tickets). A clause that only forbids the holder reselling or
  transferring a ticket is not a stop: include only listings that issue a dated ticket to the buyer.";
- the hard rules: no fabrication; fact topics only hotel, transport, place, tax, fare, price, entry, history,
  stat; never steer readers to buy direct/official or to a free/public alternative; never write "dearer than
  official"; no banned phrases; no emojis; captions describe only what is in the photo;
- "If a browser call is refused by a permission check or site approval, do not work around it: mark that seller
  'not checked'. If every partner is refused, stop and report.";
- "Do not publish, commit or edit outside content_drafts/. Reply in under 250 words."
Wait for its report. If it stopped (reseller ban, nothing readable), mark the row "dropped <date> <reason>",
add the reason to "Ruled out", and take the next row. A stop at the reseller terms, before any pricing, is cheap:
take up to 4 rows, and after two ticket stops take the next operator-run tour (husky, boat, day trip), which has no
venue to refuse resellers. A stop after pricing: at most 2 tries per run. A run should end with a page.

## 3. Edit (lead editor, before publishing)
Read the draft's opening, short-answer table, every figcaption and every FAQ. Fix, don't just note:
- prose that sends readers to the official site's own cheaper deal, a free route or "do it yourself" → delete;
- a caption that claims a place, a stop or a fact the photo or a source does not show → cut to what is in frame;
- a short-answer row for a seller marked "not checked" → delete;
- any price or rule in the verdict that is not in the table or the facts → fix or delete.

## 4. Integrate
1. `.venv/bin/python ops/tpconv.py <slug>` (must end "converted N of N").
2. Verdict: add a `"<slug>": dict(text=..., cta=("href", "Check <product> on <Partner>", "<short link>"))` entry
   to `V` in add_aeo.py, directly above the line `    "where-to-book-snow-monkey-tour": dict(`. Text: 2-3
   sentences, the pick, the dated price and the reason (cancellation, inclusions), only figures from the draft.
   The short link is the converted link of the listing the verdict names.
3. Stay-guide pointer: for each stay guide in the backlog row, run
   `grep -n '^    "where-to-stay-in-<city>": ' add_aeo.py`. A slug can appear twice in STAY_POINTERS and the
   later one silently wins, so there must be exactly one pointer entry for it.
   - If an entry exists, append one sentence to its text: "Going to X? <a href="<slug>.html">X compared</a> ...".
   - If no entry exists, add a new `("intro", '...')` entry.
4. Finder: add `("<slug>", "<short label>")` to the right region in TOURS in ops/add_finder.py.
5. `.venv/bin/python -c "import ast;ast.parse(open('add_aeo.py').read())"`
6. `.venv/bin/python publish_article.py --slug <slug> --no-audit`
7. `.venv/bin/python ops/register_ticket.py <slug> <facts-file>`. The facts file is the country file in
   data/facts, for example japan, uk, us, france, korea or singapore.
8. `zsh ops/pipeline.sh` in the background (about 10 minutes). It must print "pipeline ok".

   add_aeo.py links each "Book" cell of the short answer, the seller names in the tables and the section lines to
   the listing the page compared, and gives every partner link its rel. So: write the short-answer cell as
   "GetYourGuide: <the listing's own name>", link each listing by its name once in the sellers section, and keep
   the id of that first heading "The short answer". Two good picks for different readers (cheapest, most reviewed,
   takes children)? Add `cta2=("Check X on Y", "<short link>")` after `cta` and name that pick in the text.
   Neighbours (before the pipeline): for a city with other activity pages, add a STAY_POINTERS sentence both ways (a trip there is
   often several activities).

## 5. Check (all must pass before commit)
- `.venv/bin/python audit_site.py` → "No failures"
- `.venv/bin/python facts.py` → ends "ok"
- `.venv/bin/python test_monetization.py` → no FAIL
- `.venv/bin/python ops/check_verdicts.py` → fails only the 4 known pages (packing fragile souvenirs, solo
  safety, train vs flight, medical kit)
- the new page has one `class="gy-verdict"`, site/ and docs/ copies are identical, each stay guide links it,
  `grep -c 'aria-label="Guides by city"' site/articles/klook-vs-kkday.html` is 1.
If a check fails, fix it when the cause is clear: a failure you introduced, such as a wrong anchor or a
missing link. If not, do not commit, and do not stash or discard anything. Leave the working tree as it is,
write the failure to the log, and say so in the run's summary. The next run's precondition will see the dirty
tree and stop until someone looks.

## 6. Ship
`git add -A site docs add_aeo.py ops/add_finder.py site_taxonomy.py data` → review `git status --short` (nothing
from the gitignore list in CLAUDE.md) → commit (imperative, with the why, trailer
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`) → `git push` →
`.venv/bin/python indexnow.py --since HEAD~1`. Routine article batches are covered by the operator's standing
approval (2026-10-19). Never --no-verify.

## 7. Log
Mark the backlog row "done <date> <commit>". Append one line to ops/state/pdca_log.md:
`<date> | <slug> | pick: <partner> <price> | sellers read/not checked | commit | notes`.
