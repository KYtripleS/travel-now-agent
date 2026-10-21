#!/bin/zsh
# Post-publish build: run every page script twice (some read what others write), then restore
# the two hand-made pages from HEAD. Usage: zsh ops/pipeline.sh
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python
for i in 1 2; do
  $PY build_power_reference.py >/dev/null && $PY add_favicon.py >/dev/null && $PY add_global_nav.py --write >/dev/null && $PY add_footer.py --write >/dev/null \
  && $PY add_ga4.py G-JRGK9CN3B1 >/dev/null && $PY add_social_meta.py --write >/dev/null && $PY add_aeo.py --write >/dev/null \
  && $PY normalize_labels.py --write >/dev/null && $PY add_internal_links.py --write >/dev/null && $PY inject_tp.py >/dev/null && $PY build_stay_finder.py >/dev/null && $PY content_classes.py >/dev/null && $PY promotions.py >/dev/null && $PY link_hotel_names.py --write >/dev/null && $PY add_stay22_lma.py --write >/dev/null \
  && $PY build_library.py >/dev/null && $PY build_search_index.py >/dev/null && $PY build_map.py >/dev/null \
  && $PY x_go_links.py --write >/dev/null && $PY bust_assets.py >/dev/null || { echo "pipeline pass $i failed"; exit 1; }
done
for f in where-to-stay-in-lisbon direct-booking-vs-otas-hotel-guide; do
  git checkout HEAD -- site/articles/$f.html docs/articles/$f.html
done
$PY bust_assets.py >/dev/null
echo pipeline ok
