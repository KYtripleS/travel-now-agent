# Moving Travel Now to a custom domain (e.g. gentlyyonder.com)

Goal: serve the site at `https://gentlyyonder.com` instead of
`https://kytriples.github.io/travel-now-agent`. Follow the order exactly —
adding the CNAME before DNS resolves takes the live site down.

## Step 1 — Buy the domain
Namecheap (or any registrar). ~¥1,500/yr. Nothing else to configure yet.

## Step 2 — Point DNS at GitHub Pages
In the registrar's **Advanced DNS** panel, add these records for the **apex**
(`@`) domain:

| Type | Host | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | kytriples.github.io. |

(Optional IPv6 — add AAAA records: `2606:50c0:8000::153`, `...8001::153`,
`...8002::153`, `...8003::153`.)

DNS can take 30 min–24 h to propagate. Check with `dig gentlyyonder.com +short` —
it should return the four GitHub IPs.

## Step 2.5 — Rebrand to Gently Yonder (I do this)
The adverb domain means the brand becomes **Gently Yonder**. One command renames
all 1,266 "Travel Now" mentions (wordmark, titles, footers, JSON-LD, bio):

```
python rebrand.py --brand "Gently Yonder" --write
```

(The @TripWorldAdvice X handle and logo image files are separate — rename those
by hand if you want them changed too.)

## Step 3 — Rewrite the site's URLs (I do this)
Once you confirm the domain is yours, I run:

```
python migrate_domain.py --domain gentlyyonder.com --write
python audit_site.py            # confirm 7/8 still green
```

This swaps all 918 hard-coded `kytriples.github.io/travel-now-agent` URLs
(canonicals, sitemap, OG tags, JSON-LD) to `gentlyyonder.com`.

## Step 4 — Add the CNAME (LAST) and push
Only after `dig` shows the GitHub IPs:

```
python migrate_domain.py --domain gentlyyonder.com --write --cname
git add -A && git commit -m "Migrate to custom domain gentlyyonder.com" && git push
```

Then in **GitHub repo → Settings → Pages → Custom domain**, enter
`gentlyyonder.com`, save, and tick **Enforce HTTPS** once the certificate issues
(can take an hour).

## Step 5 — Re-establish Search Console
A custom domain is a new property to Google:
1. Add `gentlyyonder.com` as a new property in Search Console (DNS verification).
2. Submit `https://gentlyyonder.com/sitemap.xml`.
3. Keep the old property too — the old URLs 301-style resolve via the Pages
   redirect, but re-indexing the new domain takes a few weeks.

## Notes
- The `googlee46af4b13b14f75e.html` GSC verification file stays — don't delete.
- Internal links are relative (`../`, `index.html`) so they keep working; only
  the absolute base URL changes.
- Robots.txt + sitemap are rewritten automatically by the script.
- Expect a temporary ranking wobble after any domain move; it settles in 2–6
  weeks if the redirect is clean.
