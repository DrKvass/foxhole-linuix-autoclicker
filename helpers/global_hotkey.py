"""KDE global shortcut active only while the controller is running."""
import dbus
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtDBus import QDBusConnection


class GlobalHotkey(QObject):
    activated = Signal()
    COMPONENT = 'foxhole-clicker'
    ACTION = '_k_session:toggle'
    SERVICE = 'org.kde.kglobalaccel'
    INTERFACE = 'org.kde.kglobalaccel.Component'
    KEY = 0x08000000 | 0x01000003  # Qt AltModifier | Key_Backspace

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = None
        self.iface = None
        self.active = False
        self.action = dbus.Array([self.COMPONENT, self.ACTION, 'Foxhole Clicker', 'Select target / start / pause'], signature='s')

    def register(self):
        self.bus = dbus.SessionBus()
        self.iface = dbus.Interface(self.bus.get_object(self.SERVICE, '/kglobalaccel'), 'org.kde.KGlobalAccel')
        if not self.iface.isGlobalShortcutAvailable(dbus.Int32(self.KEY), self.COMPONENT):
            raise RuntimeError('Alt+Backspace is already assigned in KDE. Change the conflicting shortcut first.')
        self.iface.doRegister(self.action)
        self.path = str(self.iface.getComponent(self.COMPONENT))
        if not QDBusConnection.sessionBus().connect(self.SERVICE, self.path, self.INTERFACE, 'globalShortcutPressed', self, '1pressed(QString,QString,qlonglong)'):
            self.close()
            raise RuntimeError('Cannot listen to KDE global shortcuts.')
        assigned = self.iface.setShortcut(self.action, dbus.Array([self.KEY], signature='i'), dbus.UInt32(6))
        if self.KEY not in assigned:
            self.close()
            raise RuntimeError('KDE did not assign Alt+Backspace.')
        self.active = True

    @Slot(str, str, 'qlonglong')
    def pressed(self, component, action, timestamp):
        if component == self.COMPONENT and action == self.ACTION:
            self.activated.emit()

    def close(self):
        if self.path:
            QDBusConnection.sessionBus().disconnect(self.SERVICE, self.path, self.INTERFACE, 'globalShortcutPressed', self, '1pressed(QString,QString,qlonglong)')
            try:
                self.iface.unregister(self.COMPONENT, self.ACTION)
            except dbus.DBusException:
                pass
        self.path = None
        self.active = False
