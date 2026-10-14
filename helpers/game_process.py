#!/usr/bin/env python3
"""Detect the actual Foxhole game, excluding Steam/Wine and clicker helpers."""
import configparser
import os
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent.parent


def configured_name():
    cfg = configparser.ConfigParser()
    cfg.read(PACKAGE / 'config.ini')
    return cfg.get('Target', 'ProcessName', fallback='War-Win64-Shipping.exe')


def find_game(name=None, proc_root=Path('/proc')):
    name = (name or configured_name()).casefold()
    for proc in proc_root.iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
            actual = os.fsdecode(argv[0]).replace('\\', '/').rsplit('/', 1)[-1].casefold()
            if actual != name:
                continue
            env = dict(os.fsdecode(s).split('=', 1) for s in (proc / 'environ').read_bytes().split(b'\0') if b'=' in s)
            prefix = env.get('WINEPREFIX', '').rstrip('/')
            if prefix.endswith('/steamapps/compatdata/505460/pfx') or env.get('SteamAppId') == '505460':
                return int(proc.name)
        except (OSError, ValueError):
            continue
    return None


if __name__ == '__main__':
    if find_game() is None:
        print('Foxhole is not running. Start the game through Steam first.', file=sys.stderr)
        sys.exit(1)
