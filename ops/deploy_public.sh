#!/bin/zsh
# Publish the built site (docs/) to the public site-only repository, so the source repository
# (scripts, briefs, notes, history) can be private. 2026-11-20.
#
# The public repo holds only what gentlyyonder.com already serves, with its own history and a
# neutral commit identity: no source files, no CLAUDE.md, no machine or personal names.
#
# setup once:  PUBLIC_REPO=https://github.com/<org>/<repo>.git in .env
# usage:       zsh ops/deploy_public.sh            (after the normal commit + push)
set -euo pipefail
REPO=${0:A:h:h}
source <(grep -E '^PUBLIC_REPO=' "$REPO/.env" || true)
: "${PUBLIC_REPO:?set PUBLIC_REPO in .env first}"
WORK="$REPO/.public-site"                       # gitignored working clone

if [[ ! -d "$WORK/.git" ]]; then
  git clone -q "$PUBLIC_REPO" "$WORK" 2>/dev/null || { mkdir -p "$WORK"; git -C "$WORK" init -q -b main; git -C "$WORK" remote add origin "$PUBLIC_REPO"; }
fi
git -C "$WORK" config user.name "Gently Yonder"
git -C "$WORK" config user.email "noreply@gentlyyonder.com"
git -C "$WORK" pull -q --rebase origin main 2>/dev/null || true

rsync -a --delete --exclude '.git' "$REPO/docs/" "$WORK/"
touch "$WORK/.nojekyll"

# refuse to publish any line of ops/state/private_strings.txt (gitignored, one string per line)
PRIV="$REPO/ops/state/private_strings.txt"
[[ -s "$PRIV" ]] || { echo "deploy_public: $PRIV missing"; exit 1; }
if grep -rIl -i -F -f "$PRIV" "$WORK" --exclude-dir=.git; then
  echo "deploy_public: private string found in the files above, not publishing"; exit 1
fi

git -C "$WORK" add -A
if git -C "$WORK" diff --cached --quiet; then echo "deploy_public: nothing to publish"; exit 0; fi
git -C "$WORK" commit -q -m "Update site $(date -u +%Y-%m-%dT%H:%MZ)"
git -C "$WORK" push -q origin main
echo "deploy_public: published $(git -C "$WORK" rev-parse --short HEAD)"
