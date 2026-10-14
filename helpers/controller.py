#!/usr/bin/env python3
"""Native desktop controls; the windowless AHK worker stays in Foxhole's prefix."""
import configparser
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from PySide6.QtCore import QTimer, Qt, QPoint, QSignalBlocker
from PySide6.QtGui import QCursor, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QComboBox, QMessageBox)

from game_process import find_game

PACKAGE = Path(__file__).resolve().parent.parent
STATE = Path.home() / '.local/share/foxhole-clicker'


def send_command(verb, interval=500, remember=False, reuse=False, shift=False, cps=False):
    STATE.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.command.', dir=STATE)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(f'{verb}\n{uuid.uuid4()}\n{interval}\n{int(remember)}\n{int(reuse)}\n{int(shift)}\n{int(cps)}\n')
        os.replace(name, STATE / 'state')
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_preferences():
    try:
        data = (STATE / 'settings.ini').read_bytes()
        text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
        cfg = configparser.ConfigParser(); cfg.read_string(text)
        return max(1, min(60000, cfg.getint('Settings', 'Interval', fallback=500))), cfg.getboolean('Settings', 'Remember', fallback=False), cfg.getboolean('Settings', 'ShiftClick', fallback=False), cfg.getboolean('Settings', 'DisplayCPS', fallback=False)
    except (OSError, UnicodeError, ValueError, configparser.Error):
        return 500, False, False, False


class Controller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Foxhole Clicker')
        self.resize(470, 280)
        self.running = False
        self.started = time.time()
        self.connected = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Foxhole background clicker'))
        row = QHBoxLayout(); row.addWidget(QLabel('Click rate:'))
        self.interval = QDoubleSpinBox(); self.interval.setKeyboardTracking(False)
        interval, remember, shift, cps = read_preferences()
        self.interval_ms = interval
        self.cps_mode = QCheckBox('Clicks per second'); self.cps_mode.setChecked(cps)
        self.render_rate()
        row.addWidget(self.interval); row.addWidget(self.cps_mode); layout.addLayout(row)
        rate_note = QLabel('Requested rate; actual speed depends on Proton and the game.')
        rate_note.setWordWrap(True); layout.addWidget(rate_note)
        row = QHBoxLayout(); row.addWidget(QLabel('Input:'))
        self.input_mode = QComboBox(); self.input_mode.addItems(['Left click', 'Shift + left click'])
        self.input_mode.setCurrentIndex(int(shift)); row.addWidget(self.input_mode); layout.addLayout(row)
        self.remember = QCheckBox('Remember last point'); self.remember.setChecked(remember)
        self.reuse = QCheckBox('Use saved coordinates on next target selection')
        self.remember.setToolTip('Save the selected coordinates between launches. Turning this off deletes the saved point.')
        self.reuse.setToolTip('During Set Target, click Foxhole to identify its window, but reuse the saved coordinates instead of the new click position.')
        layout.addWidget(self.remember); layout.addWidget(self.reuse)
        row = QHBoxLayout()
        self.select = QPushButton('Set Target'); self.select.clicked.connect(lambda: self.command('SELECT'))
        self.toggle = QPushButton('Start / Pause'); self.toggle.clicked.connect(lambda: self.command('PAUSE' if self.running else 'RUN'))
        self.stop = QPushButton('Stop'); self.stop.clicked.connect(lambda: self.command('STOP'))
        leave = QPushButton('Exit'); leave.clicked.connect(self.close)
        for button in (self.select, self.toggle, self.stop, leave): row.addWidget(button)
        layout.addLayout(row)
        self.status = QLabel('Starting the invisible Proton worker…'); self.status.setWordWrap(True)
        layout.addWidget(self.status)
        hint = QLabel('Alt+Backspace: select target → start → pause.\nThe selection click also reaches the game; Esc cancels selection.')
        hint.setWordWrap(True); layout.addWidget(hint)
        self.shortcut_status = QLabel('Alt+Backspace: checking KDE shortcut…')
        self.shortcut_status.setWordWrap(True); layout.addWidget(self.shortcut_status)
        self.cursor_prompt = QLabel(None, Qt.ToolTip | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput)
        self.cursor_prompt.setAttribute(Qt.WA_ShowWithoutActivating)
        self.cursor_prompt.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.cursor_prompt.setText('Click a target point • Esc cancels')
        self.cursor_prompt.setStyleSheet('QLabel { background: #20242b; color: #ffffff; border: 1px solid #728096; border-radius: 5px; padding: 8px; }')
        self.cursor_prompt.adjustSize()
        self.prompt_timer = QTimer(self); self.prompt_timer.timeout.connect(self.position_prompt)
        self.prompt_timer.setInterval(40)
        self.hotkey = QShortcut(QKeySequence('Alt+Backspace'), self)
        self.hotkey.setAutoRepeat(False)
        self.hotkey.activated.connect(self.shortcut_action)
        self.global_hotkey = None
        try:
            if 'KDE' not in os.environ.get('XDG_CURRENT_DESKTOP', '').upper():
                raise RuntimeError('Use your desktop’s custom keyboard shortcut settings.')
            from global_hotkey import GlobalHotkey
            self.global_hotkey = GlobalHotkey(self)
            self.global_hotkey.activated.connect(self.shortcut_action)
            self.global_hotkey.register()
            self.hotkey.setEnabled(False)
            self.shortcut_status.setText('Alt+Backspace is active across the desktop.')
        except Exception as exc:
            if self.global_hotkey:
                self.global_hotkey.close()
            self.shortcut_status.setText('Desktop hotkey unavailable. Bind Alt+Backspace to helpers/toggle.sh in your desktop’s shortcut settings.')
            print(f'Optional KDE shortcut: {exc}', file=sys.stderr)
        self.set_connected(False)
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(250)
        self.interval.editingFinished.connect(self.rate_edited)
        self.cps_mode.toggled.connect(self.units_changed)
        self.remember.toggled.connect(self.save_preferences)
        self.reuse.toggled.connect(self.save_preferences)
        self.input_mode.currentIndexChanged.connect(self.save_preferences)
        self.launcher = subprocess.Popen(['bash', str(PACKAGE / 'helpers/launch-worker.sh')], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def render_rate(self):
        blocker = QSignalBlocker(self.interval)
        if self.cps_mode.isChecked():
            self.interval.setDecimals(9); self.interval.setRange(1000 / 60000, 1000)
            self.interval.setSuffix(' clicks/s'); self.interval.setSingleStep(1)
            self.interval.setValue(1000 / self.interval_ms)
        else:
            self.interval.setDecimals(0); self.interval.setRange(1, 60000)
            self.interval.setSuffix(' ms'); self.interval.setSingleStep(1)
            self.interval.setValue(self.interval_ms)

    def rate_edited(self):
        value = self.interval.value()
        self.interval_ms = max(1, min(60000, int((1000 / value if self.cps_mode.isChecked() else value) + 0.5)))
        self.render_rate()
        self.save_preferences()

    def units_changed(self):
        # Preserve the canonical interval; switching units must never change speed.
        self.render_rate()
        self.save_preferences()

    def position_prompt(self):
        pos = QCursor.pos() + QPoint(18, 24)
        screen = QApplication.screenAt(QCursor.pos())
        if screen:
            rect = screen.availableGeometry()
            pos.setX(max(rect.left(), min(pos.x(), rect.right() - self.cursor_prompt.width())))
            pos.setY(max(rect.top(), min(pos.y(), rect.bottom() - self.cursor_prompt.height())))
        self.cursor_prompt.move(pos)

    def show_prompt(self, selecting):
        if selecting:
            self.position_prompt()
            self.cursor_prompt.show()
            self.prompt_timer.start()
        else:
            self.prompt_timer.stop()
            self.cursor_prompt.hide()

    def set_connected(self, connected):
        self.connected = connected
        if not connected:
            self.show_prompt(False)
        for button in (self.select, self.toggle): button.setEnabled(connected)

    def shortcut_action(self):
        if self.connected:
            self.command('TOGGLE')

    def command(self, verb):
        try:
            send_command(verb, self.interval_ms, self.remember.isChecked(), self.reuse.isChecked(), self.input_mode.currentIndex() == 1, self.cps_mode.isChecked())
            if verb == 'SELECT':
                self.status.setText('Switch to Foxhole now and click the target point.')
            elif verb == 'RUN':
                self.running = True
            elif verb in ('STOP', 'PAUSE'):
                self.running = False
        except OSError as exc:
            self.status.setText(f'Cannot write command: {exc}')

    def save_preferences(self):
        if self.connected:
            self.command('CONFIG')

    def poll(self):
        path = STATE / 'worker-status'
        try:
            stamp = path.stat().st_mtime
            values = dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)
            fresh = stamp >= self.started and time.time() - stamp < 3
            exited = values.get('exited') == '1' or values.get('message') == 'Worker exited.'
            self.set_connected(fresh and not exited)
            if fresh:
                self.running = values.get('running') == '1'
                self.show_prompt(values.get('selecting') == '1' and not exited)
                self.status.setText(values.get('message', 'Worker ready.'))
                if exited:
                    self.timer.stop()
                    self.close()
            else:
                self.show_waiting()
        except (OSError, ValueError):
            self.set_connected(False); self.show_waiting()

    def show_waiting(self):
        if time.time() - self.started > 15:
            self.status.setText('Worker unavailable. See ~/.local/share/foxhole-clicker/launch.log. Close and relaunch to retry.')

    def closeEvent(self, event):
        self.show_prompt(False)
        if self.global_hotkey:
            self.global_hotkey.close()
        self.command('EXIT')
        event.accept()


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / 'controller.lock', 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Foxhole Clicker controller is already open. Use Alt+Tab to find it.')
        return
    app = QApplication(sys.argv)
    app.setApplicationName('Foxhole Clicker')
    if find_game() is None:
        QMessageBox.information(None, 'Foxhole Clicker', 'Start Foxhole through Steam first, then open the clicker.')
        return
    controller = Controller(); controller.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
