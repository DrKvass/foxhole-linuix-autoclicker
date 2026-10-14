#!/usr/bin/env python3
"""Create/update the desktop application entry for this copy of the package."""
import os
import shutil
from pathlib import Path
import tempfile


def exec_argument(value):
    # Desktop value decoding happens before Exec argument decoding.
    value = value.replace('%', '%%')
    value = ''.join('\\' + c if c in '\\"`$' else c for c in value)
    value = value.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return '"' + value + '"'


def desktop_entry(package):
    launcher = package / 'helpers' / 'launch.sh'
    return '\n'.join([
        '[Desktop Entry]', 'Version=1.0', 'Type=Application',
        'Name=Foxhole Clicker', 'Comment=Open the Foxhole background clicker controller',
        'Exec=' + exec_argument(shutil.which('bash') or '/bin/bash') + ' ' + exec_argument(str(launcher)),
        'Icon=input-mouse', 'Terminal=false', 'StartupNotify=false',
        'Categories=Utility;', 'Keywords=Foxhole;clicker;autoclicker;', '',
    ])


def main():
    package = Path(__file__).resolve().parent.parent
    data_home = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    if not data_home.is_absolute():
        data_home = Path.home() / '.local/share'
    destination = data_home / 'applications' / 'foxhole-clicker.desktop'
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.foxhole-clicker-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(desktop_entry(package))
        os.chmod(tmp, 0o644)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    print(f'Shortcut updated for: {package}')
    print(f'Application entry: {destination}')

if __name__ == '__main__':
    main()
