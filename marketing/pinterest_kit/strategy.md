# Travel Now — Pinterest Growth Kit

Operational guide. Start here, then use `boards.md` to create your boards and
`pins.csv` for daily upload.

---

## Where you are

- **Followers**: 0
- **Monthly impressions**: 390
- **Owned pins**: 17 (all PNG ready in `site/images/pinterest/`)
- **Rich Pins**: ✅ already configured (we set up `article:*` meta + domain
  verification in earlier commits — pins will pull article metadata from your
  site automatically)

This is the standard zero-to-one position. The number that matters is not
followers — it is **outbound clicks to the site**. Pinterest rewards accounts
whose pins send users to the source, not accounts with the most followers.

---

## Realistic timeline for click-through traffic

With consistent daily pinning (5 pins/day) and the board structure in
`boards.md`:

| Week | Monthly impressions (median) | Site clicks / mo |
|------|------------------------------|------------------|
| Now  | 390                          | 0–5              |
| 4    | 1,500–4,000                  | 10–40            |
| 8    | 5,000–15,000                 | 50–250           |
| 12   | 15,000–50,000                | 200–1,200        |
| 24   | 50,000–200,000               | 1,000–5,000      |

Pins compound. A pin you upload today may not break out for 8–12 weeks. Keep
posting through the quiet period.

---

## The 4 levers, in priority order

### 1. Volume per article (single biggest factor for new accounts)
The same article should produce **3–5 different pins** over time — different
photo, different title angle, different secondary keywords. Pinterest counts
each as fresh content; users searching different terms find different ones.

Our 17 pins is the **first wave**. The plan for waves 2 and 3 is in
`variant_patterns.md`.

### 2. SEO on title and description
- Title 30–80 chars, keyword-front-loaded ("Japan Country Profile…" not
  "A guide for…").
- Description 200–300 chars, natural language, keywords appearing naturally,
  end with a soft CTA ("Read the full guide", "See the comparison").
- Avoid the CLAUDE.md banned phrases ("must-see", "bucket list",
  "Instagram-worthy" etc.) — Pinterest's algorithm doesn't punish them, but
  the brand stays cleaner without them, and Pinterest is full of accounts
  using them, so we differentiate by *not*.

### 3. Board structure
Boards are how Pinterest categorises your account. 6 boards is the sweet spot
for our 17 pins — small enough to populate each one, large enough to cover
different searcher intents. See `boards.md`.

### 4. Daily cadence
Pinterest's algorithm weighs **recency of activity**. Pinning 5 pins on
Monday and zero for two weeks performs worse than 1 pin a day for two weeks
on the same content.

Aim for **3–5 pins/day, every day** (mix of own + curated repins from other
travel accounts you respect).

---

## What we automated for you

1. **17 pin images** at 1000×1500 with brand template (already in repo)
2. **Optimized title + description for every pin** → `pins.csv`
3. **6-board structure with keyword-rich names and descriptions** →
   `boards.md`
4. **3 variant angles per article** for waves 2 and 3 →
   `variant_patterns.md`
5. **Pinterest "Save" hover button on every article page** (next commit will
   add this — when readers hover over the inline article photos, a red
   Pinterest button appears; one-click save)
6. **Rich Pins** — already configured in earlier commits so Pinterest pulls
   article title, description, and dates automatically. No action needed.

## What you do (manual, 15 min/day)

### One-time (today)
1. Open Pinterest → Boards → create the 6 boards from `boards.md`. Copy the
   name and description exactly.
2. Verify the website link in your bio points to
   `https://kytriples.github.io/travel-now-agent/`.

### Daily (~15 minutes)
1. Open `pins.csv`. Find rows where `post_day` ≤ today.
2. For each: drag the PNG from `site/images/pinterest/` into Pinterest's
   "Create Pin" → paste title, description, link, and board from the CSV.
3. Save.

If you do this 5 days a week for 4 weeks, you finish wave 1. By then,
Pinterest API approval will likely be in and we can automate posting.

### Weekly (~10 minutes)
- Check Pinterest Trends at <https://trends.pinterest.com> — search "travel",
  "[season]", "[your next country profile destination]". Note any keyword
  that's spiking. Tell me, and I will generate a fresh pin for it.

---

## Killing pins that don't perform

After ~4 weeks, Pinterest Analytics will show impressions and outbound
clicks per pin. The standard heuristic:

- **Top 20% by impressions** → make 2 more variants (different photo /
  different title angle)
- **Bottom 50% by impressions after 4 weeks** → archive (delete on Pinterest,
  keep file in repo)

This is how you compound: kill what fails, double down on what works.

---

## Pinterest API status

Trial Access pending. Once approved:
- The disabled "Post to Pinterest" node in
  `n8n/pinterest-pin-batch.workflow.json` activates
- The Python pipeline can post a whole wave in seconds
- We will move from manual daily upload to scheduled batches

Email me / send a message when the approval comes through.
