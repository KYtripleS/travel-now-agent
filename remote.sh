#!/usr/bin/env bash
# Attach to (or create) the persistent Gently Yonder work session.
# From iPhone (Blink/Termius over Tailscale):  ssh ky@kenomacbook-air  then:  ~/travel-now-agent/remote.sh
exec tmux new-session -A -s gy -c "$HOME/travel-now-agent"
