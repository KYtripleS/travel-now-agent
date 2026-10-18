# Brief: write one "Where to Stay in <City> (2026)" guide for Gently Yonder

Repo: /Users/ky/travel-now-agent (static site; site/ is source, docs/ is published).
You write a draft and a registration file. You do NOT edit anything in site/, docs/ or any .py file,
you do NOT run publish_article.py or the pipeline, and you do NOT commit. The lead editor integrates.

The registration file goes in content_drafts/stay/<city>.json (gitignored, and safe from the
temporary-folder cleanup); photo downloads go in any scratch folder you like.

## Your outputs
1. `content_drafts/where-to-stay-in-<city>.final.md` (Markdown with inline HTML figures)
2. `content_drafts/where-to-stay-in-<city>.meta.json`
3. `content_drafts/stay/<city>.json`, the registration file (schema below)
4. Optional: downloaded photo files in a scratch folder (to look at them)

## Copy the model exactly
Read `content_drafts/where-to-stay-in-new-york.final.md` and `.meta.json` and
`content_drafts/where-to-stay-in-paris.final.md` first. Match their structure, tone, length
(2,200-2,800 words) and conventions:
- H1 title with the year and the hook: "Where to Stay in Rome (2026): The Best Areas, 12 Hotels and the City Tax".
  Never use straight double quotes in the title (they break HTML attributes); use “curly” ones.
- Opening: what makes this city's hotel bill different (usually the tourist tax), then one paragraph:
  "This guide covers N areas ... 12 hotels ... The hotels are researched picks, chosen for location,
  what each property publishes and consistent guest feedback, and each was checked as operating in
  October 2026. No hotel pays to appear here."
- "## The short answer" table (If you want… | Stay in | Why), 4-6 areas.
- A tax section with a table of the official rates (by star category if the city does that), and one
  worked example labelled as our arithmetic.
- "## Getting in from the airport(s), and around": official fares and routes only.
- One H2 per area ("## Trastevere: evenings and village streets"), 1-2 paragraphs on the area, then
  "**Where to stay in <area>**" and 2-3 hotels as bullets in the NYC format:
  `- **[Hotel Name](official hotel website)**, splurge|comfortable|good value|budget. Facts from the hotel's own site. Choose it for .... *Watch out:* ....`
- "## How to book <City>": count the tax, watch the season, check room size, compare totals (link
  `hotel-booking-sites-comparison.html`).
- "## All 12 at a glance" table: Hotel | Area | Tier | Best for | Watch out for. Hotel names here must be
  printed exactly as in the bullets.
- "## Before you go": eSIM + insurance links that exist in site/articles/ (check with ls; e.g.
  `best-travel-esim-2026.html`, `best-travel-insurance-2026.html`, a country eSIM page if one exists).
- "## Sources & further reading": official URLs you actually opened, then
  "Official websites of each hotel named above, checked in October 2026".
- Closing italic disclaimer line, as in NYC.
- meta.json: title, slug, description (150-160 chars, names the areas and the tax), category "Stay",
  primary_keyword "where to stay in <City>", faq (6 Q&As; each answer must match the body).
- Exactly 12 hotels, spread across tiers (at least 2 budget/good value, at least 2 splurge).

## Photos (required: 5-6 figures)
Get candidates from Pexels with the repo's helper (the API key is in .env; never print it):
```
cd /Users/ky/travel-now-agent && .venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv('/Users/ky/travel-now-agent/.env')
import enhance_article_photos as e, json; print(json.dumps(e.pexels_photo('Rome Trastevere street'), indent=1))"
```
(If that helper's return shape differs, read its source; you may call the Pexels search API the same
way it does, with per_page up to 15.) Download each candidate at w=940 into a scratch folder and
LOOK at it with the Read tool before using it. The alt text must describe only what is visibly in the
frame (never the heading's claim); reject photos that show a different city or are unidentifiable.
Figure markup, exactly:
```
<figure class="article-figure">
  <img src="https://images.pexels.com/photos/<id>/pexels-photo-<id>.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" alt="..." loading="lazy" />
  <figcaption>Short caption. <span class="photo-credit">Photo: <a href="<photographer url>" rel="noopener nofollow">Name</a> / <a href="<photo page url>" rel="noopener nofollow">Pexels</a></span></figcaption>
</figure>
```
Place one under the intro or the short answer, and one in most area sections.

## Research rules (hard)
- Web access: try WebSearch/WebFetch first. If they error, use the browser tools
  (mcp__Claude_Browser__*): ALWAYS open your own tab with `tabs_create` and pass that tabId on every
  call; never touch other tabs; close your tab at the end. Search with
  `https://html.duckduckgo.com/html/?q=...` and read pages with get_page_text (max_chars ≤ 6000).
  Do not log in anywhere, accept no cookie banners beyond "reject"/"necessary only", stop at CAPTCHAs.
- WebFetch summaries can misread pages (hidden text, overlays). For any claim that changes the advice
  (a scheme ended, a price changed), confirm it in the page's raw HTML or a second source.
- Every number (tax rates, fares, journey times, room sizes, prices) comes from an official source
  (city/government, the transport operator, the airport, the hotel's own site). Record each in the
  registration file's facts with its URL.
- Each hotel: confirm on its own official site that it is operating (not "permanently closed", not
  "opening 2027"), and take its facts only from there. Name only real, checkable places.
- Booking.com: for each hotel, open its Booking.com hotel page and confirm it is that exact hotel in
  that city (in the browser: navigate, then javascript_tool returning document.title plus the text of
  `[data-testid="PropertyHeaderAddressDesktop-wrapper"]`; no await/setTimeout in javascript_tool).
  Record the canonical URL in the form `https://www.booking.com/hotel/<cc>/<slug>.html` (strip query
  strings and language suffixes like .en-gb). If you cannot confirm it, record null. Never guess a slug.
- Never claim a stay or visit ("we stayed", "I loved"); neutral editorial voice, "we" for the editors.
- British spelling. No emojis. Banned phrases: hidden gem, magical, must-see, bucket list, secret spot,
  off the beaten path, Instagram-worthy. No legal guarantees.
- No affiliate links in the draft (the build adds them). Internal links only to files that exist in
  site/articles/ (check with ls). Link the city's existing guides if they exist (first-timers guide,
  things to do, eSIM).

## Registration file schema (content_drafts/stay/<city>.json)
```json
{
  "slug": "where-to-stay-in-rome",
  "stay22": {"area": "Centro Storico", "lat": 41.8986, "lng": 12.4769, "zoom": 15,
             "address": "Piazza Navona, Rome, Italy"},
  "hotels": {"Hotel Name exactly as printed in bold": "https://www.booking.com/hotel/it/....html or null"},
  "verdict_hotels": ["3 hotel names from the 12, one per tier, best first-trip picks"],
  "verdict": {"text": "<= 55 words, like the NYC one: 'For a first trip, stay in X: ... Choose Y for ..., Z for .... The tax is ...'",
              "link_text": "the area name as it appears in text", "cta_label": "See hotels around <area>"},
  "card_hook": "<= 110 chars, for the Keep reading card",
  "related": ["articles/<existing-file>.html", "... 4-5 existing related guides"],
  "llms_line": "- [Where to Stay in Rome (2026)](https://gentlyyonder.com/articles/where-to-stay-in-rome.html): one sentence",
  "facts": [
    {"id": "it.rome.tourist-tax", "topic": "tax|fare|transport|place|hotel|price|history",
     "claim": "one sentence with the number and its scope", "checked": "2026-10-13",
     "sources": [{"url": "...", "kind": "official|operator|news", "title": "..."}],
     "used_in": {"articles/where-to-stay-in-rome.html": ["2-3 short phrases copied VERBATIM from your final.md body text (no markdown symbols, no '...')"]}}
  ],
  "notes": "anything the editor should double-check"
}
```

When done, reply briefly: word count, the 12 hotels with Booking.com found/null, facts list, photos
used, anything unverified you left out.
