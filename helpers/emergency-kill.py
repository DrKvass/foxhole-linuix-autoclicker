#!/usr/bin/env python3
"""Only signal exact clicker command lines owned by this Linux user."""
import os
from pathlib import Path
import signal
import sys

def is_clicker(argv):
    if not argv:
        return False
    base = lambda s: s.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return (base(argv[0]) == "foxholeclicker.exe" or
            (base(argv[0]) in {"autohotkey.exe", "autohotkeyu64.exe", "autohotkeyu32.exe"}
             and any(base(arg) == "foxholeclicker.ahk" for arg in argv[1:])))

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"--list", "--terminate", "--force"}:
        raise SystemExit("Usage: emergency-kill.py --list|--terminate|--force")
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise SystemExit('Emergency stop requires Python with pidfd support (Linux 5.3+). Use helpers/exit.sh instead.')
    found = False
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            argv = [s.decode(errors="replace") for s in (proc / "cmdline").read_bytes().split(b"\0") if s]
            if not is_clicker(argv):
                continue
            # pidfd prevents a recycled PID from receiving the signal.
            fd = os.pidfd_open(int(proc.name))
            try:
                again = [s.decode(errors="replace") for s in (proc / "cmdline").read_bytes().split(b"\0") if s]
                if again != argv:
                    continue
                found = True
                print(proc.name, *argv)
                if sys.argv[1] != "--list":
                    signal.pidfd_send_signal(fd, signal.SIGKILL if sys.argv[1] == "--force" else signal.SIGTERM)
            finally:
                os.close(fd)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    if not found:
        print("No exact clicker process found; no process was signalled.")

if __name__ == "__main__":
    main()
