# Foxhole Clicker

A small background clicker for Foxhole on Linux. Pick a point, set a rate, and
keep using your mouse elsewhere. Supports left click and Shift + left click.
It exits when the game closes.

## Setup

You'll need **x86-64 Linux**, Python 3.10+, Steam with Foxhole running through
Proton, and [native Protontricks](https://github.com/Matoking/protontricks).
`protontricks-launch` must be on your PATH. Use X11, or Wayland with Xwayland.

Extract the folder anywhere, open a terminal there, and run:

```bash
bash ./setup.sh
```

Setup uses your installed PySide6, or installs it in a local `.venv`. It also
downloads the official AutoHotkey v1 runtime and checks its SHA-256. No root
access is needed. If Python reports that venv is missing, install your distro's
Python venv package and retry.

Start Foxhole first, then:

```bash
bash ./launch.sh
```

For an application-menu shortcut, run `bash ./install-shortcut.sh`. Run it again
after moving the folder. Keep the whole folder together.

## Use

**Alt+Backspace** selects a target if none is set, starts if paused, and pauses
if running. Selection shows a prompt beside the cursor: click the point within
15 seconds. That click reaches the game. Selecting a point doesn't start clicking.
The buttons do the same jobs; **Stop** retains the target and **Exit** closes everything.

- **Input:** left click or Shift + left click.
- **Clicks per second:** switches units. 20 ms = 50 clicks/s. The minimum is 1 ms,
  but actual speed depends on Proton and the game.
- **Remember last point:** saves coordinates between launches.
- **Use saved coordinates:** your next selection identifies the game window but
  reuses the saved point. Leave this off to pick a new position.

On **KDE**, the desktop-wide hotkey is automatic if `dbus-python` is installed.
On **other desktops**, bind Alt+Backspace to `bash "/full/path/to/foxhole-clicker/helpers/toggle.sh"`
in keyboard settings. The in-game fallback and controller buttons also remain
available. Desktop hotkeys require the controller to be open.

## Notes

Tested in game on CachyOS/KDE with Proton; other distros haven't been tested in
game. Flatpak/sandboxed Steam setups may need extra filesystem access and are not
covered by this launcher. Pure Wayland without Xwayland isn't supported.

Settings and logs live in `~/.local/share/foxhole-clicker/`. If startup fails,
check `controller.log` and `launch.log`. Reselect after changing the game's layout
or resolution. Keep the game restored, not minimized.

For an unresponsive clicker, run `python3 ./helpers/emergency-kill.py --terminate`
(Linux 5.3+). Don't kill the entire Wine server—it would close Foxhole too.

This ZIP contains source only: no personal settings, binaries or fonts. The
project code is MIT licensed; downloaded dependencies keep their own licenses.
Use it where automation is allowed.
