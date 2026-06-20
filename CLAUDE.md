# Travel Now — Project Rules for Claude / Cursor

This file is read by Claude Code, Cursor, and any AI assistant working on this repo.
Read it BEFORE making changes. It captures non-obvious conventions and hard rules.

---

## 🎯 Project overview

- **Name:** Travel Now
- **What it is:** An independent English-language travel-preparation editorial project.
- **Live URL:** https://kytriples.github.io/travel-now-agent/
- **Host:** GitHub Pages (publishes `docs/`)
- **Built by:** A small editorial team (no individual is named publicly).

---

## 🔒 PRIVACY — non-negotiable

These rules exist because the operator runs this as a side project and does NOT
want personal identity associated with the site or this repo.

### Never publish or commit
- Real name of the operator.
- The phrase "AI 会社員" or any reference to a public AI/note persona.
- Personal note.com / Threads / personal X account names or URLs.
- Personal email addresses, phone numbers, home addresses.
- Internal monetisation notes or affiliate application drafts.

### OK to use publicly
- The anonymous brand X handle `@TripWorldAdvice` (already referenced in footers / JSON-LD).
- The brand name "Travel Now".
- Editorial "we" — never "I" tied to a real identity.

### Gitignored (must stay gitignored)
```
affiliate_applications/
note_drafts/
threads_drafts/
daily_status/
branding/ai-kaishain/
branding/personal-account/
MOBILE_HANDOFF.md
data/monetization_log.csv
monthly_metrics/
```
Verify with `git check-ignore -v <path>` before adding any new sensitive file.

---

## 📁 Repository structure

```
site/         <- SOURCE files. Edit here.
docs/         <- PUBLISHED files (served by GitHub Pages). Must mirror site/.
branding/     <- editorial guidelines, brand assets (most gitignored)
affiliate_applications/  <- tracker + draft application messages (gitignored)
build_site.py            <- regenerates site/index.html "AUTO-GENERATED" sections from products.csv
audit_site.py            <- pre-deploy health check (sitemap, links, sync, affiliate tags)
add_ga4.py               <- inject/update/remove GA4 snippet across all HTML
add_privacy_footer.py    <- one-shot patcher (already applied)
```

### Hard rule: site/ ↔ docs/ must stay in sync.
After every edit, copy the changed file from `site/` to `docs/` (same relative path).
`audit_site.py` checks this.

---

## 🛠️ Standard commands

```bash
# Build (regenerate index.html sections from CSV)
python build_site.py

# Pre-deploy health check
python audit_site.py

# Add/update GA4 across all pages (current ID: G-JRGK9CN3B1)
python add_ga4.py G-JRGK9CN3B1

# Check GA4 coverage
python add_ga4.py --check

# Render a Pinterest pin from SVG template
rsvg-convert -w 1000 -h 1500 site/images/pinterest/<name>.svg -o site/images/pinterest/<name>.png
cp site/images/pinterest/<name>.png docs/images/pinterest/<name>.png
```

---

## 🎨 Brand system

| Token | Value |
|---|---|
| `--navy` | `#172033` (primary surface) |
| `--gold` | `#C9A84C` (accent, CTAs) |
| `--surface` | `#F8F4E9` (cream, light surfaces) |
| Body font | Georgia, "Times New Roman", serif |
| Display font | Georgia (700 weight, tight letter-spacing) |
| Logo / wordmark | "Travel Now" — never reduce to an initial |

### Editorial voice
- Neutral, layered, "explain what was lost and what survives" tone.
- Academic-style sourcing in country/city profiles (Reynolds, Pascoe, public-institution stats).
- Multiple perspectives on contested history (Indigenous, colonial, modern).
- **Banned phrases:** "hidden gem", "magical", "must-see", "bucket list", "secret spot",
  "off the beaten path", "Instagram-worthy".
- **Banned claims:** "guarantees entry", "you won't be denied", any legal/medical guarantee,
  any immigration advice beyond publicly available preparation guidance.

---

## 💰 Affiliate rules

- **Amazon Associates tag:** `packlightpick-20` — ALL Amazon links must include this.
  `audit_site.py` enforces this.
- **Awin** — applications tracked in `affiliate_applications/status-tracker.md`.
- **FTC disclosure** — every page with affiliate links must include an explicit
  Disclosure paragraph in its footer (see existing articles for pattern).
- **`rel` attributes** — affiliate links must have `rel="nofollow sponsored noopener"`.
- **No affiliate links in:** sensitive historical sections, About, Editorial Guidelines,
  Privacy. Affiliates only in: practical prep sections, comparison articles, product cards.

---

## 📊 Analytics & SEO

- **GA4 measurement ID:** `G-JRGK9CN3B1`
- **GA4 config:** `anonymize_ip: true`, no Google Signals, no remarketing.
- **Privacy policy:** `/privacy.html` — must stay in sync with what GA4 actually does.
- **Sitemap:** `/sitemap.xml` — add every new HTML page here, then re-submit in GSC.
- **robots.txt:** `/robots.txt` — references sitemap, blocks `*.backup.css`.
- **GSC verification file:** `/googlee46af4b13b14f75e.html` — DO NOT delete or rename.

---

## 📌 Pinterest pin template

- **Size:** 1000 × 1500 px (2:3 ratio)
- **Master SVG template:** any file in `site/images/pinterest/*.svg`
  (Japan country profile is the cleanest reference).
- **Pattern:** navy gradient bg + cream/colour medallion with iconic shape + huge serif title
  + 4 bullet markers (gold diamond) + gold CTA pill + URL hint.
- **Render to PNG** via `rsvg-convert` (librsvg). DO NOT use Canva — breaks brand consistency.
- **Avoid emoji** in the SVG — `rsvg-convert` doesn't ship colour emoji fonts; use SVG shapes.

---

## 🔄 Git workflow

- **Never auto-commit.** Always show the diff and the exact commit command to the user;
  the user runs it.
- **Never auto-push.** Same rule.
- **Never `--no-verify` / `--no-gpg-sign`** unless the user explicitly asks.
- **Commit message style:** imperative, descriptive, includes the *why* not just the *what*.
  Multiple changes can be one commit if they belong together (e.g. "Add GA4 + privacy +
  footer links").
- **Co-Authored-By line:** the user is fine with one; example:
  ```
  Co-Authored-By: Claude <noreply@anthropic.com>
  ```
- **Branch:** work on `main`. There is no separate dev branch.

---

## ✅ Pre-deploy checklist

Before suggesting `git push`, run mentally / via tools:

1. `python build_site.py` — regenerates AUTO-GENERATED sections
2. `python audit_site.py` — must pass 7/8 (1 warning about style.backup.css is OK)
3. All JSON-LD blocks parse (use `json.loads` per block)
4. All new pages added to `sitemap.xml`
5. All new HTML pages have GA4 snippet (use `python add_ga4.py --check`)
6. All new pages have Privacy link in footer (run `python add_privacy_footer.py`)
7. `site/` and `docs/` are in sync for every changed file
8. No personal-info file accidentally staged (check `git status` against the gitignore list)

---

## 🚫 Hard "don't"s

- Don't create README files unless explicitly requested.
- Don't add emojis to code/HTML/CSS files unless the user asks.
- Don't reproduce copyrighted content (quotes > 15 words, song lyrics, etc).
- Don't use browser automation / paid AI image generation without user permission.
- Don't apply to new affiliate networks on the user's behalf — they must do it themselves.
- Don't enter credentials, payment info, or authenticate as the user anywhere.
