#!/usr/bin/env bash
set -euo pipefail
package=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
state_dir="$HOME/.local/share/foxhole-clicker"
mkdir -p -- "$state_dir"
if [[ -z "${DISPLAY:-}" ]]; then
    echo "An X11 display or Xwayland is required. Enable Xwayland for your desktop." >&2
    exit 1
fi
bash "$package/helpers/python.sh" -c 'from PySide6 import QtWidgets' || { echo 'Run bash ./setup.sh first.' >&2; exit 1; }
command -v protontricks-launch >/dev/null || { echo 'Install native Protontricks; protontricks-launch must be on PATH.' >&2; exit 1; }
[[ -f "$package/AutoHotkey.exe" ]] || { echo 'Missing AutoHotkey.exe. Run bash ./setup.sh.' >&2; exit 1; }
nohup env QT_QPA_PLATFORM=xcb bash "$package/helpers/python.sh" "$package/helpers/controller.py" > "$state_dir/controller.log" 2>&1 < /dev/null &
printf 'Controller log: %s/controller.log\n' "$state_dir"
