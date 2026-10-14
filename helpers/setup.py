#!/usr/bin/env python3
"""Install the GUI dependency locally and fetch the official AHK v1 runtime."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import venv
import zipfile

PACKAGE = Path(__file__).resolve().parent.parent
URL = 'https://github.com/AutoHotkey/AutoHotkey/releases/download/v1.1.37.02/AutoHotkey_1.1.37.02.zip'
SHA256 = '6f3663f7cdd25063c8c8728f5d9b07813ced8780522fd1f124ba539e2854215f'


def runtime_from_zip(data):
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('AutoHotkey download checksum did not match; nothing installed.')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        runtime = archive.read('AutoHotkeyU64.exe')
    if not runtime.startswith(b'MZ'):
        raise ValueError('Invalid AutoHotkey executable.')
    return runtime


def install_runtime():
    dest = PACKAGE / 'AutoHotkey.exe'
    if dest.is_file():
        print('Keeping existing AutoHotkey.exe.')
        return
    print('Downloading AutoHotkey v1.1.37.02 from its official GitHub release…', flush=True)
    request = urllib.request.Request(URL, headers={'User-Agent': 'Foxhole-Clicker-Setup'})
    with urllib.request.urlopen(request, timeout=60) as response:
        runtime = runtime_from_zip(response.read())
    fd, temp = tempfile.mkstemp(prefix='.autohotkey-', dir=PACKAGE)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(runtime)
        os.replace(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print('AutoHotkey installed; archive SHA-256 verified.')


def gui_available(python):
    return subprocess.run([str(python), '-c', 'from PySide6 import QtWidgets'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def install_gui():
    local_python = PACKAGE / '.venv/bin/python'
    if local_python.exists():
        if gui_available(local_python):
            return
    elif gui_available(sys.executable):
        return
    print('Installing PySide6 in this folder’s .venv…', flush=True)
    # Reuse distro modules (including optional dbus-python) without changing them.
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(PACKAGE / '.venv')
    subprocess.run([str(local_python), '-m', 'pip', 'install', '-r', str(PACKAGE / 'requirements.txt')], check=True)


def main():
    if sys.platform != 'linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise SystemExit('This package targets x86-64 Linux with Steam/Proton.')
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10 or newer is required.')
    install_gui()
    install_runtime()
    if not shutil.which('protontricks-launch'):
        print('Next: install native Protontricks using your distro or pipx. protontricks-launch must be on PATH.')
    print('Ready. Start Foxhole through Steam, then run: bash ./launch.sh')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Setup failed: {exc}\nIf venv is unavailable, install your distro’s Python venv package. You can rerun setup.')
