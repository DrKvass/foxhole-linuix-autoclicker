#!/usr/bin/env bash
set -euo pipefail
package=$(dirname -- "$(readlink -f -- "$0")")
exec bash "$package/helpers/python.sh" "$package/helpers/install-shortcut.py"
