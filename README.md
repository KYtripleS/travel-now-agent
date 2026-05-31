# Travel Now Agent

Travel Now Agent is an AI-assisted workflow for building and operating a lightweight travel-prep media project.

Live site: https://kytriples.github.io/travel-now-agent/

X account: https://x.com/TripWorldAdvice

## What this project does

- Generates English X/Twitter post candidates using Gemini (3 per day: morning / afternoon / evening)
- Generates Threads post drafts in Japanese and English
- Exports post ideas to CSV
- Maintains a lightweight Travel Now hub site
- Manages starter product ideas in CSV
- Builds the website from product data
- Generates long-form English Markdown drafts (Medium, Substack, note, site)
- Generates Japanese note drafts for the series「会社員、AIでメディアを作る。」
- Generates short-form video scripts for YouTube Shorts, Instagram Reels, and TikTok
- Supports a one-command daily workflow

## Daily workflow

Run:

```
python daily_run.py
```

This workflow:
1. Shows recent posted content to avoid repeating topics
2. Generates 30 X post candidates via Gemini
3. Rebuilds the Travel Now site from product data
4. Selects 3 X posts (morning / afternoon / evening) and writes `top_posts.csv` + `data/x_post_schedule.csv`
5. Displays the 3 posts in copy-ready format
6. Shows git status
7. Shows revenue action suggestions (article pipeline)
8. Shows the money path (what to publish, where to send traffic)
9. Shows or generates Japanese note drafts
10. Shows Threads drafts if they exist for today

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
| `generate_video_scripts.py` | `video_scripts/YYYY-MM-DD-{slug}/` | YouTube Shorts / Reels / TikTok |
| `generate_threads_posts.py` | `threads_drafts/YYYY-MM-DD-{mode}.md` | Threads（手動投稿） |

## Threads drafts

Generate Threads post drafts for manual posting:

```
python generate_threads_posts.py                         # dry run
python generate_threads_posts.py --write                 # japanese_ai_media (default)
python generate_threads_posts.py --write --mode travel_now
python generate_threads_posts.py --write --all           # both modes
python generate_threads_posts.py --write --force         # overwrite today's files
```

Each draft file (`threads_drafts/YYYY-MM-DD-{mode}.md`) contains:
- 5 standalone posts
- 2 short thread sequences (2–3 posts each)
- 3 soft CTA variants

**Constraints (never change):**
- No auto-posting to Threads
- No Meta API or Threads API
- No login, no browser automation
- All posts are copy-pasted manually

### Modes

| Mode | Language | Voice | CTA |
|---|---|---|---|
| `japanese_ai_media` | 日本語 | 20代会社員・夢追いチャレンジャー・軽い関西弁 | note記事・シリーズフォロー |
| `travel_now` | English | Practical travel-prep friend | Checklist Generator |

### Logging Threads activity

After posting, run:

```
python update_content_log.py --write
```

This appends a row to `data/monetization_log.csv` for each Threads draft file.
Update `clicks`, `likes`, `sales`, `revenue_yen` manually after each post.

## Long-term goal

The long-term goal is to turn Travel Now into an AI-assisted travel media operation that can generate content, manage product data, update a website, and support scalable publishing workflows across English and Japanese channels.

## Disclaimer

This project is experimental. It does not provide legal, medical, visa, insurance, financial, or safety advice.
