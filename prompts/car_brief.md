# Brief: write one "Renting a car in <Place>" decision page for Gently Yonder

Repo: /Users/ky/travel-now-agent (static site; site/ is source, docs/ is published).
You write a draft, a links file and a facts file. You do NOT edit anything in site/, docs/, data/ or any
.py file, you do NOT run publish_article.py or the pipeline, and you do NOT commit. The lead editor integrates.

Why these pages: car hire is the largest single earner for travel publishers on our affiliate network
(one published report: DiscoverCars was 75% of a travel blog's network income in 2024), and our own
best pages are decision pages with a same-day price table and an honest verdict. A reader here has
already decided where to go and is asking: do I need a car, what will it really cost, and where do I book it.

## Your outputs
1. `content_drafts/<slug>.final.md` (Markdown with inline HTML figures)
2. `content_drafts/<slug>.meta.json`
3. `content_drafts/<slug>.links.json`: every price you print (row, seller, url = the page you read it
   on, price_seen, date_seen, pickup, dropoff, residence, currency)
4. `content_drafts/cars/<slug>.json`: {"facts": [...]} in the facts schema of prompts/stay_brief.md
   (with "evidence" quotes and "used_in" phrases copied verbatim from your body text, no markdown symbols),
   plus "related" (4-5 existing site/articles/*.html), "card_hook" (<= 110 chars), "llms_line", "notes".

## Read first, once
- `prompts/stay_brief.md`: follow its sections "Working economically", "Photos" and "Research rules"
  exactly (own browser tab, never the operator's Chrome, evidence quotes, no trips claimed, banned
  phrases, British spelling, no emojis). Ignore its hotel and registration parts.
- The model for structure and tone: `content_drafts/where-to-buy-disneyland-paris-tickets.final.md`
  (and its .meta.json). Same conventions; length 1,800-2,600 words.

## Structure
- H1: "Renting a Car in <Place> (2026-27): Do You Need One, What It Costs and Where to Book". No straight
  double quotes in the title.
- Opening, 2 short paragraphs: the honest answer to "do I need a car here" (where a car is essential,
  where public transport or tours do the job: say so plainly, even if it means fewer bookings), then the
  disclosure line: DiscoverCars is a partner and pays us a commission; the rental firms' own sites pay us nothing.
- "## The short answer" table (If you… | Do this | Why), 4-5 rows (e.g. city only, ring road, winter, families).
- "## What a week costs: one date, every seller": ONE pick-up about 3-6 weeks ahead, 7 days, the main
  airport, return to the same place (state all of it), read on one day (state it). Rows = 2-3 car classes
  that fit the place (e.g. small manual, small automatic, 4x4/SUV where the roads need it). Columns =
  DiscoverCars (lowest listed offer in that class, with the supplier name it shows) and 2-3 of the biggest
  local or international firms read on their OWN sites for the same dates. One currency; prefer USD and a
  driver residence of United States if the site lets you choose; otherwise state the residence and currency
  shown. Each price is a link to the page it was read on (raw URL; the editor converts DiscoverCars links).
  A site that blocks automated reading is "not checked", with the reason. Bold the lowest per row.
  Caption: dates, residence, "prices change daily".
- Verdict rule (operator, 2026-11-19): the verdict points to DiscoverCars as the quick, safe way to book
  (many suppliers side by side, free cancellation terms as its page states); never recommend booking on a
  firm's own site and never send the reader off to compare. Say plainly where DiscoverCars is cheaper; keep
  other firms' prices in the table as neutral facts without "dearer" sentences. Never invent a saving.
- "## Insurance and the excess": what the basic price includes, the typical excess/deposit shown, the
  firms' own cover vs DiscoverCars' Full Coverage as its own terms describe it (who pays the desk first,
  how a claim works). Quote or closely paraphrase the terms pages, with the date read. No advice beyond
  what the terms say.
- "## Rules of the road that change the booking": licence and International Driving Permit rules, minimum
  age, winter tyres or road closures, tolls/parking, anything place-specific (e.g. F-roads in Iceland,
  Japanese IDP convention rules, left-hand driving). From official sources only (government, police,
  road authority, embassy).
- "## When not to rent": the trips where a car is the wrong tool, and what to book instead (link existing
  site pages: tours, rail, transfers).
- "## Before you go": existing site guides for that place (check with ls: stay guide, first-timers guide,
  eSIM, insurance).
- "## Sources & further reading": official URLs you opened, then the rental pages with the date read.
- Closing italic line as in the model.
- meta.json: title, slug, description (150-160 chars), category "Booking & tours", primary_keyword
  "car rental <place>", faq (6 Q&As, each matching the body).
- 4-5 Pexels figures of the place's roads and landscapes (alt text = only what is in frame).

## Web access
DiscoverCars' search widget does not work in the built-in browser (a script fails to load), but its
airport landing page lists its lowest current offers for the page's own default dates (shown in the form,
e.g. "Sat, Nov 21" to "Sun, Nov 29"). Open the landing page with `?currency=USD`
(e.g. https://www.discovercars.com/iceland/keflavik/kef?currency=USD), take the default pick-up and
drop-off dates and times it shows, and use THOSE dates for every seller in the table. The driver
residence is fixed by location (it shows Japan): state it in the caption. Read the per-day price and
multiply by the days shown, labelled as our arithmetic, or print per-day prices throughout. Call mcp__Claude_Browser__tabs_create FIRST and pass its tabId on
every call: a navigate without your own tab acts on the operator's tab and is refused. If tabs_create says
the pane is not open, open your own tab with preview_start {url} and use only that tab. Close your tab at the end.
Do not enter any personal data in booking forms; stop at the results page (never proceed to a booking step).

When done, reply briefly (under 250 words): word count, the price table in plain text, which sellers
were not checked and why, facts list (ids), photos used, anything unverified you left out.

- Buying rule (operator, 2026-11-20, every article): never recommend booking or buying direct or on the
  official site, never list direct-booking discounts or perks as a reason to leave, and never send the reader
  off to compare or check other sites; that wastes their time. Name the partner that is the quick, safe buy.
  Official facts (dates, rules, prices in tables, safety rules) stay as neutral facts. Never lie or invent a saving.
