#!/usr/bin/env bash
# Daily GSC report wrapper (invoked by launchd: com.gentlyyonder.gsc).
# Hardcoded repo path so it works regardless of launchd's cwd/$0.
cd /Users/ky/travel-now-agent || exit 1
mkdir -p gsc_reports
/Users/ky/anaconda3/bin/python3 gsc_analyze.py >> gsc_reports/cron.log 2>&1
