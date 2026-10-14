#!/usr/bin/env python3
"""Launch on the display of Foxhole's existing Wine session, if available."""
import os
from pathlib import Path
import sys


def find_game_display(proc_root=Path('/proc')):
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            if (proc / 'comm').read_text().strip() not in ('wineserver', 'wineserver64'):
                continue
            entries = (proc / 'environ').read_bytes().split(b'\0')
            env = dict(os.fsdecode(s).split('=', 1) for s in entries if b'=' in s)
            prefix = env.get('WINEPREFIX', '').rstrip('/')
            if not (prefix.endswith('/steamapps/compatdata/505460/pfx') or env.get('SteamAppId') == '505460'):
                continue
            display = env.get('DISPLAY')
            if not display:
                continue
            result = {'DISPLAY': display}
            auth = env.get('XAUTHORITY')
            if auth and auth.startswith('/'):
                # Steam's container has a different filesystem view.
                candidates = [proc / 'root' / auth.lstrip('/'), Path(auth)]
                for candidate in candidates:
                    if candidate.is_file() and os.access(candidate, os.R_OK):
                        result['XAUTHORITY'] = str(candidate)
                        break
                else:
                    raise RuntimeError('Cannot read the game display authentication file; restart Foxhole and retry.')
            return result
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return {}


def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: game-display.py COMMAND [ARG ...]')
    env = os.environ.copy()
    try:
        overrides = find_game_display()
    except RuntimeError as exc:
        raise SystemExit(str(exc))
    if overrides:
        env.update(overrides)
        print('Using Foxhole display ' + overrides['DISPLAY'], flush=True)
    os.execvpe(sys.argv[1], sys.argv[1:], env)

if __name__ == '__main__':
    main()
