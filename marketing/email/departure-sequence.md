# Departure countdown: four emails timed to the reader's trip (2026-11-20)

Replaces "one weekly email to everyone" for readers who give a destination and a departure date.
Each email does one job at the moment that job is due. Paste-ready for MailerLite.

## Setup (once the mailing service exists)

- Fields: `destination` (text, e.g. "Japan") and `departure_date` (date).
- The newsletter form (Tally) asks for both; Ready Score already knows the destination (`?dest=`).
- Automation: trigger "date field: departure_date", four steps at 45, 30, 14 and 7 days before.
  A reader who signs up later than a step's day skips that step (never send two in one day).
- Variants: one Japan version (our deepest guides) and one general version. `{{destination}}` fills the rest.
- Every email: sender "Gently Yonder", a working reply-to, the unsubscribe link, and the line
  "Some links are partner links: we may earn a commission at no extra cost to you."

## Honesty rules for these emails

- No countdown clocks, no "only 2 rooms left", no invented price rises. Say what is true: a
  free-cancellation rate holds a room without committing you.
- Link to our guides, which are kept current, rather than stating rules in the email, which cannot be corrected.
- Name the partner wherever a link leads to one.

---

## D-45: cover (insurance)

**Subject:** {{destination}} in six weeks: the one thing to sort first
**Preview:** Cover bought early protects the money you spend from now on.

Hi,

Your trip to {{destination}} is about six weeks away. Before anything else, sort travel insurance:
cover that starts when you buy it protects the flights and rooms you book from now on, if you have to cancel.

- Which policy fits your trip, by type of traveller: https://gentlyyonder.com/articles/best-travel-insurance-2026.html
- Not sure you need it at all? We answer that honestly: https://gentlyyonder.com/articles/is-travel-insurance-worth-it.html
- Two minutes, no sign-up: https://gentlyyonder.com/tools/insurance-finder.html

Next email in two weeks: where to stay.

---

## D-30: a bed (hotels)

**Subject:** {{destination}}: hold a room now, decide later
**Preview:** A free-cancellation rate costs nothing to keep.

Hi,

A month to go. If you have not booked where you sleep, this is the week: book a rate with free
cancellation and you hold the room without committing to it. If you find something better, cancel before the deadline the booking shows.

- Which area to stay in, with our picks at three budgets: https://gentlyyonder.com/stay/index.html
- Answer four questions, get the area that fits: https://gentlyyonder.com/tools/stay-finder.html
- Japan: https://gentlyyonder.com/articles/where-to-stay-in-tokyo.html

Read the cancellation line before you pay: that one line is the difference between a hold and a commitment.

---

## D-14: data (eSIM)

**Subject:** Two weeks out: your phone in {{destination}}
**Preview:** Install the eSIM at home, switch it on when you land.

Hi,

Two weeks to go: a good time to buy an eSIM and install it on home Wi-Fi, so it works the moment you land.

- Which eSIM, by how you use your phone: https://gentlyyonder.com/articles/best-travel-esim-2026.html
- Japan: https://gentlyyonder.com/articles/best-esim-japan-2026.html
- How much data you will actually use: https://gentlyyonder.com/tools/esim-finder.html

Check your phone is unlocked and eSIM-capable before you buy (Settings shows it).

---

## D-7: last checks

**Subject:** One week to {{destination}}: the last checks
**Preview:** Passport, entry form, bag. Ten minutes tonight.

Hi,

A week to go. Ten minutes tonight saves an hour at the airport:

- Run your Ready Score: it names anything still open, from passport validity to entry forms:
  https://gentlyyonder.com/#ready
- Japan: register on Visit Japan Web before you fly: https://gentlyyonder.com/articles/visit-japan-web-guide.html
- Pack carry-on only, item by item: https://gentlyyonder.com/articles/carry-on-packing-list-10-day-japan.html

Have a good trip. Reply to this email if something in our guides turned out wrong: we fix it and log it publicly
(https://gentlyyonder.com/corrections.html).
