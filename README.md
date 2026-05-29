# Travel Now Agent

Travel Now Agent is an AI-assisted workflow for building and operating a lightweight travel-prep media project.

Live site: https://kytriples.github.io/travel-now-agent/

X account: https://x.com/TripWorldAdvice

## What this project does

- Generates English X/Twitter post candidates using Gemini
- Exports post ideas to CSV
- Maintains a lightweight Travel Now hub site
- Manages starter product ideas in CSV
- Builds the website from product data
- Generates long-form English Markdown drafts (Medium, Substack, note, site)
- Generates Japanese note drafts for the series「会社員、AIでメディアを作る。」
- Supports a one-command daily workflow

## Daily workflow

Run:

python daily_run.py

This workflow generates post candidates, rebuilds the website, shows top posts, and displays git status.

## Tech stack

- Python
- Gemini API
- CSV workflow
- HTML/CSS
- GitHub Pages

## Monetization direction

The project is designed to gradually support affiliate monetization through travel-prep categories such as packing, eSIM, flight comfort, charging, travel safety, and camera travel gear.

Current product links are Amazon search-page URLs with the affiliate tag `packlightpick-20`. They can be replaced with specific product ASINs once the best-performing products are identified.

## Affiliate management

| File | Purpose |
|---|---|
| `affiliate_links.csv` | Master list of all affiliate links — category, URL, placement, status |
| `affiliate_click_log.csv` | Manual click / order / revenue log (update after each publish) |
| `affiliate_tools.py` | CLI utilities: list links, check disclosures, check tags, weekly summary |

```
python affiliate_tools.py list                        # active links with tag check
python affiliate_tools.py list --all                  # include inactive
python affiliate_tools.py category "Flight Comfort"   # links for one category
python affiliate_tools.py check-disclosures           # scan HTML for disclosure text
python affiliate_tools.py check-placeholders          # scan products.csv for missing tags
python affiliate_tools.py weekly-summary              # last 7 days from click log
python affiliate_tools.py weekly-summary --weeks 4    # last 4 weeks
```

**Constraints (never change):**
- No Amazon Product Advertising API
- No Amazon scraping
- No automatic fetching of prices, reviews, or images
- All links are manually entered; `affiliate_tools.py` only reads — never writes to any product file

## Content pipelines

| Script | Output | Platform |
|---|---|---|
| `main.py` | `posts.csv`, `top_posts.csv` | X/Twitter |
| `generate_article.py` | `site/articles/*.html` | Travel Now site |
| `generate_draft.py` | `content_drafts/*.md` | Medium / Substack / note |
| `generate_note_draft.py` | `note_drafts/*.md` | note（日本語） |

## Long-term goal

The long-term goal is to turn Travel Now into an AI-assisted travel media operation that can generate content, manage product data, update a website, and support scalable publishing workflows across English and Japanese channels.

## Disclaimer

This project is experimental. It does not provide legal, medical, visa, insurance, financial, or safety advice.
