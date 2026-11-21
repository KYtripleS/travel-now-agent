# Data pitches: earn citations with what only we have (2026-11-21)

An outside review (2026-11-20) said the site will not count as a primary source until others cite it:
other media quoting us, reader reviews on other sites, mentions in search. Baseline on 21 Nov 2026:
Bing knows 0 inbound links from 0 domains (`ops/bing.py`).

Expert-quote replies are in `marketing/backlinks/haro-pitches.md`. This file adds pitches built on our own
data, because a journalist can cite a number with a source far more easily than an opinion.

## What we can offer that others cannot
- **Open fact ledger**: https://gentlyyonder.com/open-data.html. More than 3,200 facts with sources and check
  dates, as CSV and JSON under CC BY 4.0. It is rebuilt on every publish (`ops/build_open_data.py`).
- **Tourist taxes data report**: https://gentlyyonder.com/articles/tourist-taxes-around-the-world-2026-data.html
  covers 85 cities and comes with a CSV.
- **Public corrections log**: https://gentlyyonder.com/corrections.html. It shows each fix in public.

## Rules (all hard)
- Sign as "Casey, editor at Gently Yonder". Use only the brand X handle and the brand email (operator_todo #5).
  Never use the operator's real name.
- Quote only numbers that are in the ledger. Give the checked date and the official source with the number.
- Never pay for a link, a placement or a review. Never swap links. Never post or send fake reviews.
- Every send is the operator's decision. Claude drafts. The operator, or Claude after an explicit yes, sends.
- Log every send in `marketing/outreach/log.md`: date, outlet, request and outcome.

## Where requests come from (free for sources)
These were checked on 2026-11-21. Sign up with the brand email; it needs operator_todo #5 first.
- **Source of Sources**: free daily emails of journalist requests.
- **SourceBottle**: free for sources. Good for Australian, UK and travel requests.
- **Qwoted**: has a free tier and the most requests; filter by "travel".
- **X**: search `#journorequest travel` and sort by Latest. The operator replies by hand from @GentlyYonder.

## Pitch 1: tourist taxes are rising in 2027 (timely: November–January)
Subject: Data: what tourist taxes add to a 3-night stay in 85 cities, and the 2027 rises

> Hi [name], I saw your piece on [topic]. We keep a city-by-city ledger of tourist and hotel taxes, each rule
> checked against the city or tax authority. Some figures:
> - On one standard stay (3 nights, 2 adults, a US$200 room), the tax is about US$104 in Chicago and
>   about US$96 in Washington DC.
> - Copenhagen, Dublin, London and Madrid charge no accommodation tax.
> - Tokyo moves to 3% in April 2027, and Vienna to 8% in July 2027.
>
> The table and the CSV are free to use with a link: [report URL]. Every row has its official source and check date.
> Casey, editor at Gently Yonder

Before sending, re-run `.venv/bin/python ops/build_tax_report.py`. Then confirm each number above against the
report's current text, because the figures change when the ledger is rechecked.

## Pitch 2: the open ledger, for data, AI and fact-check writers
Subject: Free dataset: 3,200 travel facts, each with its official source and the date it was checked

> Hi [name], we publish the fact ledger behind our travel guides as open data (CC BY 4.0): hotel, fare, tax and
> entry facts for 45 countries and cities. Each fact has its source, the kind of source, the day it was last
> checked, and a note when something could not be confirmed. Here is how often travel facts change: in our
> November recheck, 11 of 110 overdue facts had changed, and the corrections page lists each one.
> [open-data URL]. Casey, editor at Gently Yonder

## Pitch 3: what changed this month (monthly; only when there are real changes)
Use the month's entries on corrections.html. Send nothing in a month with no real change.

## Reader reviews
- Trustpilot profile: operator_todo #6. When `data/contact.json` "trustpilot_url" is set, the contact page links it.
- Ask every reader the same way: no gating to happy readers and no rewards.
