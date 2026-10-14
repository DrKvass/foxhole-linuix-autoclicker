#!/usr/bin/env bash
set -euo pipefail
umask 077
package=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
state_dir="$HOME/.local/share/foxhole-clicker"
mkdir -p -- "$state_dir"
command -v protontricks-launch >/dev/null || { echo "Install protontricks first." >&2; exit 1; }
bash "$package/helpers/python.sh" "$package/helpers/game_process.py" || exit 1
# Never inherit a stale RUN when opening the GUI.
bash "$package/helpers/stop.sh"
win_state="Z:${state_dir//\//\\}"
if [[ ! -f "$package/AutoHotkey.exe" ]]; then
    echo "AutoHotkey.exe v1 runtime is required beside FoxholeClicker.ahk." >&2
    exit 1
fi
win_script="Z:${package//\//\\}\\FoxholeClicker.ahk"
args=("$package/AutoHotkey.exe" /ErrorStdOut "$win_script" "$win_state")
nohup bash "$package/helpers/python.sh" "$package/helpers/game-display.py" protontricks-launch --no-bwrap --appid 505460 "${args[@]}" > "$state_dir/launch.log" 2>&1 < /dev/null &
printf 'Launch requested. Log: %s/launch.log\n' "$state_dir"
