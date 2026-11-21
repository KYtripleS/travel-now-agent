# X: what makes posts travel (2026-11-21)

X's published ranking weights (xai-org/x-algorithm, checked 2026-09-25):
- reply ×5, reply between accounts that follow each other +15;
- quote ×5, share by DM ×5, **share via copy link ×20**;
- follow ×4, like ×0.5, opening a link ×0.2.

New accounts (≤1,000 followers) get a boost on posts under 48 hours old. A post that only sends people to the
site is ranked on its weakest signal. A post that is useful by itself on X is ranked on its strongest.

## What the queue does now (Claude)
- **Picture cards with the numbers** (ops/x_cards.py → site/images/x/). They are made to be saved and shared. Every figure is from the fact ledger.
- **About half the posts carry no link.** They give the whole answer on X.
- **The first line is the surprise:** a contrast, a deadline, or a figure people do not expect.
- **Some posts end in a plain question** to invite replies: "Which one surprised you?", "Would you pay for the refund?"
  Questions must be real, never bait, never fake urgency.
- Never recycled, every post new (x_queue_check.py). No emojis, no banned phrases.

## What only you can do (15 minutes, the days you can)
1. **Pin the tourist-tax card post** (id 1100) when it goes out. It is the most shareable thing we have.
2. **Reply to people, not brands.** Search `tourist tax`, `Japan trip tips`, `northern lights Rovaniemi`,
   `Eiffel Tower tickets`, `#journorequest travel` (Latest). Answer the question in the reply itself, with one
   figure. Add a link only if they ask. Replies are the strongest signal X has, and automated replies break X's rules.
3. **Reply to every reply under our posts within a few hours.** Replies between accounts that follow each other score highest.
4. **Quote, don't just repost.** When a big travel account posts news we have data on, quote it with our figure.
5. Check views in X's own analytics once a week. Tell Claude which posts did best, and the next batch follows them.

## Not doing
Buying followers or engagement, follow/unfollow loops, automated replies or DMs, engagement-bait giveaways,
fake urgency, or posts about anything we have not checked.
