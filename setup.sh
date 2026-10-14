#!/usr/bin/env bash
set -euo pipefail
package=$(dirname -- "$(readlink -f -- "$0")")
exec python3 "$package/helpers/setup.py" "$@"
