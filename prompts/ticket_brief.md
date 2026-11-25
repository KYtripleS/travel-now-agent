# Brief: write one "Where to buy <Attraction> tickets" comparison for Gently Yonder

Repo: /Users/ky/travel-now-agent (static site; site/ is source, docs/ is published).
You write a draft, a links file and a facts file. You do NOT edit anything in site/, docs/, data/ or any
.py file, you do NOT run publish_article.py or the pipeline, and you do NOT commit. The lead editor integrates.

Why these pages: the two ticket comparisons we have (Disneyland Paris, Universal Studios Japan) are the
site's best pages for readers sent by ChatGPT and for partner clicks. Readers arrive ready to buy and
want one thing: where to buy this ticket for my date, and what the difference is.

## Your outputs
1. `content_drafts/<slug>.final.md` (Markdown with inline HTML figures)
2. `content_drafts/<slug>.meta.json`
3. `content_drafts/<slug>.links.json`: every reseller price you print, in the model's format
   (row, seller, url = the listing page you read it on, price_seen, date_seen, visit_date, currency)
4. `content_drafts/tickets/<slug>.json`: {"facts": [...]} in the facts schema of prompts/stay_brief.md
   (with "evidence" quotes and "used_in" phrases copied verbatim from your body text), plus
   "related" (4-5 existing site/articles/*.html), "card_hook" (<= 110 chars), "llms_line", "notes".

## Read first, once
- `prompts/stay_brief.md`: follow its sections "Working economically", "Photos" and "Research rules"
  exactly (own browser tab, never the operator's Chrome, evidence quotes, no stays claimed, banned
  phrases, British spelling, no emojis). Ignore its hotel and registration parts.
- The model: `content_drafts/where-to-buy-disneyland-paris-tickets.final.md`, `.meta.json`, `.links.json`.
  Copy its structure, tone and conventions; length 1,800-2,600 words.

## Structure (as in the model)
- H1 with the year span and the sellers: "<Attraction> Tickets (2026-27): Official Site vs Klook, GetYourGuide, ...".
  No straight double quotes in the title.
- Opening: what actually differs between sellers for this ticket (price, date rules, timed entry, sell-outs,
  what is included), then the disclosure line naming which sellers are partners and that the official
  site pays us nothing.
- "## The short answer" table (If you want… | Buy from | Why), 4-5 rows.
- "## The same-day price table": the main ticket types every seller lists, ONE visit date about 2-4 weeks
  ahead (state it), read on one day (state it), one currency. Official price beside each reseller.
  Each reseller price is a link to the listing it was read on (raw listing URL; the editor converts
  to partner links). A seller that blocks automated checks is "not checked", with the reason. Bold the
  lowest figure per row. Caption with the dates and "they change daily".
- Verdict rule (operator, 2026-11-19): never recommend buying from the official site and never send the
  reader off to compare other sites; that wastes their time. The verdict, short answer, opening and FAQ
  name the partner seller that is the safe, quick buy (cheapest partner, or best terms: free cancellation,
  instant confirmation, a seller the attraction itself names), with true reasons. Say plainly where a
  reseller is cheaper. Keep the official price in the table as a neutral fact, but do not write sentences
  saying a reseller is dearer than the official site. Never invent a saving; never lie; keep safety facts
  (ID rules, which sellers the attraction recognises).
- "## What each seller's listing says": official, then each reseller: cancellation terms, entry rules,
  what is not included, quoted or closely paraphrased from the listing, with the date read.
- A section on the attraction's own rules that change the buying decision (timed slots, ID name on ticket,
  release dates, sell-out pattern, free days, child ages), from the official site only.
- "## Before you go": links to existing site guides for that city (check with ls: stay guide, eSIM, insurance).
- "## Sources & further reading": official URLs you opened, then the reseller listings with the date read.
- Closing italic line as in the model.
- meta.json: title, slug, description (150-160 chars), category "Booking & tours", primary_keyword
  "<attraction> tickets", faq (6 Q&As, each matching the body).
- 4-5 Pexels figures of the attraction itself (alt text = only what is in frame).

## Web access for prices
Reseller sites (GetYourGuide, Klook, Viator, KKday) answer WebFetch with 403, and some official ticket
sites show a bot check. Read listings and calendars in your own built-in browser tab (allowed for this
work since 2026-11-16; rules as in stay_brief.md). Call tabs_create FIRST and pass its tabId on every
call: a navigate without your own tab acts on the operator's tab and is refused. A page that still blocks
the tab is "not checked".
Lessons from the daily runs (weekly PDCA 2026-11-23):
- Klook blocked the built-in browser tab too in 2 of 2 runs (22 and 23 Nov). Try it once; if it blocks,
  write "Klook: not checked (blocks automated reading)" and move on. Do not retry or look for a way round.
- Read every seller in the same currency. If one seller shows another currency (GetYourGuide stayed in
  USD on 23 Nov while the others showed JPY), switch that site's currency selector first. If it will not
  switch, give the table one note on it and do not bold a "cheapest" across currencies.

Before you start pricing, read the official site's terms on resellers. If it refuses tickets bought from
resellers (as Sagrada Família's does), stop and report: that page is not a comparison.

Editor's integration (not the agent's job): reseller hrefs -> Travelpayouts short links
(ops/tp_deeplinks.create), publish_article.py, `ops/register_ticket.py <slug> <facts-file>`, then the
verdict (add_aeo.V), the stay guide pointer (STAY_POINTERS) and any why-now line by hand.

## Sellers to check
Official site first. Then Klook, GetYourGuide, Viator, Tiqets and KKday where they list this ticket
(we have all five as partners through Travelpayouts). Read each listing for your chosen date. If a
seller does not sell this ticket, say so in one line rather than leaving it out silently.

When done, reply briefly (under 250 words): word count, the price table in plain text, which sellers
were not checked and why, facts list (ids), photos used, anything unverified you left out.

- Buying rule (operator, 2026-11-20, every article): never recommend booking or buying direct or on the
  official site, never list direct-booking discounts or perks as a reason to leave, and never send the reader
  off to compare or check other sites; that wastes their time. Name the partner that is the quick, safe buy.
  Official facts (dates, rules, prices in tables, safety rules) stay as neutral facts. Never lie or invent a saving.

Free and official alternatives (operator, 2026-11-20, every article): do not steer readers to a free,
public or official alternative instead of the partner product the guide is about (no "you don't need a
tour, take the bus", no "the public boat is the best value", no "the official app's discount beats the
pass"). Say what the product gives, who it suits and when it pays off, with true numbers. Never invent a
reason to buy, and never hide a fact a reader needs to stay safe or legal.

## Lessons from 21 November 2026 (read before writing)
- Run as a general-purpose agent: the article-writer agent has no browser tools. Load the browser with
  ToolSearch "select:mcp__Claude_Browser__tabs_create,mcp__Claude_Browser__navigate,mcp__Claude_Browser__get_page_text,mcp__Claude_Browser__find,mcp__Claude_Browser__computer,mcp__Claude_Browser__tabs_close".
  Call tabs_create first, pass its tabId on every call, and close the tab at the end. Never inject scripts into pages.
- Mention the official site's prices only in the table's official column, and in the one "own pages" paragraph as rules.
  Never write prose about the official site's own cheaper packages, guided tours or transfer deals.
- No section or FAQ on getting there without the product ("how do I get there without a coach package",
  "take the train instead"). Transport facts appear only as part of what a listing includes.
- No short-answer row or bullet for a seller you could not read. Just mark it "not checked" in the table.
- Partner links may be Markdown links or <a href>. Use the raw listing URL; the editor converts it.

## Lessons from 25 November 2026
- Say the minimum age, pickup point, duration, group size and cancellation of every listing, or "not stated":
  listings for the same outing differ (one aurora chase takes no under-8s).
- The short answer's "Book" cell is "Seller: the listing's own name", and the sellers section links that same name,
  so the build can link the cell to exactly that listing.
- Give a second pick when it suits a different reader (most reviewed, takes children, leaves from another place).
  Say the review score and count when the listing shows them.
