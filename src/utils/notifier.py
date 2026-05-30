"""Windows notification utilities for todo reminders."""

import subprocess
import sys
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QTimer, QObject, Signal


class ReminderChecker(QObject):
    """Periodic checker for todo reminders, built on Qt's event loop."""

    reminder_triggered = Signal(object)  # emits Todo

    def __init__(self, db, check_interval_ms: int = 60000, parent=None):
        super().__init__(parent)
        self._db = db
        self._timer = QTimer(self)
        self._timer.setInterval(check_interval_ms)
        self._timer.timeout.connect(self._check_reminders)

    def start(self):
        self._check_reminders()  # immediate first check
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _check_reminders(self):
        todos = self._db.get_todos_to_remind()
        for todo in todos:
            self.reminder_triggered.emit(todo)
            self._db.mark_reminded(todo.id)


_WIN10TOAST_AVAILABLE = False
try:
    from win10toast import ToastNotifier
    _WIN10TOAST_AVAILABLE = True
except ImportError:
    pass


def send_notification(title: str, message: str, duration: int = 5):
    """Send a Windows toast notification.

    Prefers win10toast if installed; falls back to PowerShell BurntToast or
    MessageBox.
    """
    if _WIN10TOAST_AVAILABLE:
        try:
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=duration, threaded=True)
            return
        except Exception:
            pass

    # Fallback: use PowerShell
    try:
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $template.GetElementsByTagName('text')
        $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
        $textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('StickyNotes').Show($toast)
        """
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, timeout=10,
        )
    except Exception:
        # Last resort: Windows MessageBox (blocks, but works)
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, message, title, 0x40  # MB_ICONINFORMATION
        )