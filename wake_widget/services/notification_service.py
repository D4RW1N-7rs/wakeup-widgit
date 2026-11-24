"""Desktop notification service using libnotify and notify-send."""

import os
import shutil
import subprocess
from typing import Optional

from wake_widget.constants import ALERT_SVG_PATH, APP_NAME

try:
    import gi
    gi.require_version('Notify', '0.7')
    from gi.repository import Notify
    HAS_LIBNOTIFY = True
except (ImportError, ValueError):
    HAS_LIBNOTIFY = False


class NotificationService:
    """Sends and manages desktop notifications for user inactivity."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._notify_inited = False
        self._active_notification = None
        self._last_notify_proc: Optional[subprocess.Popen] = None

        if HAS_LIBNOTIFY and self.enabled:
            try:
                Notify.init(APP_NAME)
                self._notify_inited = True
            except Exception:
                self._notify_inited = False

    def show_alert(
        self,
        title: str = '⏰ Inactivity Alert!',
        body: str = '4 minutes elapsed without activity.\nMove mouse or press any key to reset!',
        urgent: bool = True,
    ) -> None:
        if not self.enabled:
            return

        icon_path = ALERT_SVG_PATH if os.path.exists(ALERT_SVG_PATH) else 'dialog-warning'

        # Try native libnotify
        if self._notify_inited and HAS_LIBNOTIFY:
            try:
                if self._active_notification is None:
                    self._active_notification = Notify.Notification.new(title, body, icon_path)
                else:
                    self._active_notification.update(title, body, icon_path)

                if urgent:
                    self._active_notification.set_urgency(Notify.Urgency.CRITICAL)
                self._active_notification.show()
                return
            except Exception:
                pass

        # Fallback to notify-send CLI
        notify_send = shutil.which('notify-send')
        if notify_send:
            cmd = [
                notify_send,
                '-a', APP_NAME,
                '-u', 'critical' if urgent else 'normal',
                '-i', icon_path,
                title,
                body,
            ]
            try:
                self._last_notify_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    def dismiss(self) -> None:
        """Dismisses the active notification when user returns."""
        if self._notify_inited and self._active_notification:
            try:
                self._active_notification.close()
            except Exception:
                pass
            self._active_notification = None
