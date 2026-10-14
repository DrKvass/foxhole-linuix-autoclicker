#!/usr/bin/env bash
set -euo pipefail
package=$(dirname -- "$(dirname -- "$(readlink -f -- "$0")")")
if [[ -x "$package/.venv/bin/python" ]]; then
    exec "$package/.venv/bin/python" "$@"
fi
exec python3 "$@"
