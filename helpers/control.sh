#!/usr/bin/env bash
set -euo pipefail
umask 077
case "${1:-}" in RUN|STOP|PAUSE|EXIT|TOGGLE) verb=$1 ;; *) echo "Usage: $0 RUN|STOP|PAUSE|EXIT|TOGGLE" >&2; exit 2 ;; esac
state_dir="$HOME/.local/share/foxhole-clicker"
mkdir -p -- "$state_dir"
tmp=$(mktemp "$state_dir/.command.XXXXXXXX")
trap 'rm -f -- "$tmp"' EXIT
printf '%s\n%s\n' "$verb" "$(date +%s%N)-$$" > "$tmp"
mv -f -- "$tmp" "$state_dir/state"
