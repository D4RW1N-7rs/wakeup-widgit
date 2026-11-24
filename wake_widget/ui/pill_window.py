"""Always-on-top GNOME Top Bar & Desktop Pill Widget for Wake Widget."""

import math
import os
import sys
import time
from typing import Callable, Optional, Tuple

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk

from wake_widget.config import ConfigService
from wake_widget.constants import (
    APP_NAME,
    STATE_ACTIVE,
    STATE_ALERT,
    STATE_COUNTDOWN,
)
from wake_widget.core.activity_monitor import ActivityMonitor
from wake_widget.core.state_machine import WakeStateMachine
from wake_widget.services.notification_service import NotificationService
from wake_widget.services.sound_service import SoundService
from wake_widget.services.x11_topbar import (
    BUTTON1_MASK,
    BUTTON2_MASK,
    X11TopBarInputMonitor,
    is_x11_session,
)
from wake_widget.ui.popup_window import PopupWindow
from wake_widget.ui.ring_widget import ProgressRing
from wake_widget.ui.styles import enable_rgba


def format_mmss(seconds: float) -> str:
    sec = max(0, int(math.ceil(seconds)))
    return f'{sec // 60:02d}:{sec % 60:02d}'


format_time_mmss = format_mmss


class PillWindow(Gtk.Window):
    """Sleek top bar capsule pill docking beside Xattendo on the GNOME panel."""

    def __init__(
        self,
        config_service: ConfigService,
        activity_monitor: ActivityMonitor,
        sound_service: SoundService,
        notification_service: NotificationService,
        fast_test: bool = False,
        test_alert: bool = False,
    ) -> None:
        self.config_service = config_service
        self.config = config_service.config
        self.activity_monitor = activity_monitor
        self.sound_service = sound_service
        self.notification_service = notification_service

        self._top_bar_mode = bool(self.config.top_bar_mode) and is_x11_session()
        win_type = Gtk.WindowType.POPUP if self._top_bar_mode else Gtk.WindowType.TOPLEVEL
        super().__init__(type=win_type)

        idle_delay = 3.0 if fast_test else self.config.idle_delay_seconds
        timer_duration = 5.0 if fast_test else self.config.timer_duration_seconds

        self.state_machine = WakeStateMachine(
            idle_delay_seconds=idle_delay,
            timer_duration_seconds=timer_duration,
            on_state_changed=self._on_state_changed,
            on_alert_triggered=self._on_alert_triggered,
            on_alert_dismissed=self._on_alert_dismissed,
        )

        self._pos_x: int = self.config.top_bar_x or 1320
        self._pos_y: int = 2

        # Raw Top Bar XInput2 Drag State
        self._raw_dragging = False
        self._raw_drag_button = 0
        self._raw_drag_moved = False
        self._raw_drag_start_x = 0
        self._raw_drag_start_y = 0
        self._raw_win_start_x = 0
        self._raw_hovered = False

        # Floating GTK Drag State
        self._floating_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._current_state = STATE_ACTIVE
        self._x11_monitor: Optional[X11TopBarInputMonitor] = None

        # Setup Window Properties
        self.get_style_context().add_class('wake-transparent')
        self.set_title(APP_NAME)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_accept_focus(False)
        self.set_resizable(False)
        self.stick()
        enable_rgba(self)

        self._build_ui()

        # Popup window for details
        self.popup_win = PopupWindow(
            on_test_alert=self.state_machine.trigger_test_alert,
            on_reset=self.state_machine.reset,
            on_toggle_sound=self._on_toggle_sound,
            on_quit=self._on_quit,
        )

        if self._top_bar_mode:
            self._x11_monitor = X11TopBarInputMonitor(
                on_button_press=self._on_raw_button_press,
                on_button_release=self._on_raw_button_release,
                on_motion=self._on_raw_motion,
                on_screensaver_changed=lambda _: None,
            )
            self._x11_monitor.start()
        else:
            self.add_events(
                Gdk.EventMask.BUTTON_PRESS_MASK
                | Gdk.EventMask.BUTTON_RELEASE_MASK
                | Gdk.EventMask.POINTER_MOTION_MASK
            )
            self.connect('button-press-event', self._on_floating_press)
            self.connect('button-release-event', self._on_floating_release)
            self.connect('motion-notify-event', self._on_floating_motion)

        self.connect('destroy', self._on_destroy)

        self.show_all()
        GLib.idle_add(self._apply_initial_position)

        if test_alert:
            self.state_machine.trigger_test_alert()

        # Update loop (100ms)
        self._timer_id = GLib.timeout_add(100, self._on_tick)

    def _build_ui(self) -> None:
        event_box = Gtk.EventBox()
        event_box.set_visible_window(False)
        self.add(event_box)

        self.pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pill.get_style_context().add_class('wake-pill')
        self.pill.get_style_context().add_class('state-active')
        event_box.add(self.pill)

        # 1. Circular Progress Ring (size 16 matching Xattendo)
        self.ring = ProgressRing(size=16)
        self.ring.set_valign(Gtk.Align.CENTER)
        self.pill.pack_start(self.ring, False, False, 0)

        # 2. Monospace Time Label (font-size 11.5px matching Xattendo)
        self.time_lbl = Gtk.Label(label='04:00')
        self.time_lbl.set_direction(Gtk.TextDirection.LTR)
        self.time_lbl.get_style_context().add_class('wake-pill-time')
        self.pill.pack_start(self.time_lbl, False, False, 0)

    def _get_monitor_metrics(self) -> Tuple[Gdk.Rectangle, int]:
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo = monitor.get_geometry()
        wa = monitor.get_workarea()
        raw_panel_h = wa.y - geo.y
        panel_h = raw_panel_h if 16 <= raw_panel_h <= 64 else 28
        return (geo, panel_h)

    def _top_bar_y(self) -> int:
        geo, panel_h = self._get_monitor_metrics()
        _, height = self.get_size()
        return geo.y + max(0, (panel_h - height) // 2)

    def _move_to(self, x: int, y: int) -> None:
        self._pos_x = x
        self._pos_y = y
        self.move(x, y)

    def get_screen_rect(self) -> Tuple[int, int, int, int]:
        width, height = self.get_size()
        if self._top_bar_mode:
            return (self._pos_x, self._pos_y, width, height)
        px, py = self.get_position()
        return (px, py, width, height)

    def _clamp_position(self, x: int) -> Tuple[int, int]:
        geo, _ = self._get_monitor_metrics()
        width, _ = self.get_size()
        min_x = geo.x + 4
        max_x = geo.x + geo.width - max(width, 70) - 4
        clamped_x = max(min_x, min(x, max_x))
        return (clamped_x, self._top_bar_y())

    def _apply_initial_position(self) -> bool:
        if self._top_bar_mode:
            target_x = self.config.top_bar_x or 1320
            cx, cy = self._clamp_position(target_x)
            self._move_to(cx, cy)
            if cx != self.config.top_bar_x:
                self.config.top_bar_x = cx
                self.config_service.save()
        else:
            wx = self.config.widget_x or 1320
            wy = self.config.widget_y or 32
            self.move(wx, wy)
        return False

    def _on_tick(self) -> bool:
        idle_seconds = self.activity_monitor.get_idle_seconds()
        state = self.state_machine.update(idle_seconds)

        if state == STATE_ACTIVE:
            self.time_lbl.set_text(format_mmss(self.state_machine.timer_duration_seconds))
            self.ring.set_data(STATE_ACTIVE, 0.0)
        elif state == STATE_COUNTDOWN:
            self.time_lbl.set_text(format_mmss(self.state_machine.countdown_remaining))
            self.ring.set_data(STATE_COUNTDOWN, self.state_machine.countdown_progress)
        else:
            self.time_lbl.set_text('00:00')
            self.ring.set_data(STATE_ALERT, 1.0)

        if self.popup_win.get_visible():
            self.popup_win.update_state(self.state_machine, self.config.sound_enabled)

        return True

    def _on_state_changed(self, old_state: str, new_state: str) -> None:
        ctx = self.pill.get_style_context()
        ctx.remove_class(f'state-{old_state}')
        ctx.add_class(f'state-{new_state}')

    def _on_alert_triggered(self) -> None:
        if self.config.sound_enabled:
            self.sound_service.start_ticking()
        if self.config.notification_enabled:
            self.notification_service.show_alert(
                title='⏰ Inactivity Warning!',
                body='4 minutes elapsed without activity.\nMove mouse or press any key!',
            )

    def _on_alert_dismissed(self) -> None:
        self.sound_service.stop_ticking()
        self.notification_service.dismiss()

    def _on_toggle_sound(self) -> None:
        self.config.sound_enabled = not self.config.sound_enabled
        self.sound_service.sound_enabled = self.config.sound_enabled
        self.config_service.save()
        if not self.config.sound_enabled:
            self.sound_service.stop_ticking()
        if self.popup_win.get_visible():
            self.popup_win.update_state(self.state_machine, self.config.sound_enabled)

    # --- Top Bar Mode XInput2 Raw Handlers ---

    def _x11_to_logical(self, rx_px: int, ry_px: int) -> Tuple[int, int]:
        scale = max(1, self.get_scale_factor())
        return (rx_px // scale, ry_px // scale)

    def _hit_test_top_bar(self, lx: int, ly: int) -> bool:
        if not self.get_visible():
            return False
        geo, panel_h = self._get_monitor_metrics()
        px, py, pw, ph = self.get_screen_rect()
        top_edge = min(py, geo.y)
        bottom_edge = max(py + ph, geo.y + panel_h)
        return (px <= lx <= px + pw) and (top_edge <= ly <= bottom_edge)

    def _set_raw_hover(self, hovered: bool) -> None:
        if hovered == self._raw_hovered:
            return
        self._raw_hovered = hovered
        ctx = self.pill.get_style_context()
        if hovered:
            ctx.add_class('wake-pill-hover')
        else:
            ctx.remove_class('wake-pill-hover')

    def _on_raw_button_press(self, button: int, rx_px: int, ry_px: int) -> None:
        lx, ly = self._x11_to_logical(rx_px, ry_px)
        if not self._hit_test_top_bar(lx, ly):
            if self.popup_win.get_visible():
                self.popup_win.hide()
            return

        if button in (1, 2):
            self._raw_dragging = True
            self._raw_drag_button = button
            self._raw_drag_moved = False
            self._raw_drag_start_x = lx
            self._raw_drag_start_y = ly
            self._raw_win_start_x = self._pos_x
        elif button == 3:
            self.popup_win.hide()
            self._show_context_menu()

    def _on_raw_motion(self, rx_px: int, ry_px: int, mask: int) -> None:
        lx, ly = self._x11_to_logical(rx_px, ry_px)
        self._set_raw_hover(self._hit_test_top_bar(lx, ly))
        if not self._raw_dragging:
            return

        expected_mask = BUTTON1_MASK if self._raw_drag_button == 1 else BUTTON2_MASK
        if (mask & expected_mask) == 0:
            self._finish_raw_drag(self._raw_drag_button)
            return

        dx = lx - self._raw_drag_start_x
        if abs(dx) > 4:
            self._raw_drag_moved = True
            if self.popup_win.get_visible():
                self.popup_win.hide()
            nx, ny = self._clamp_position(self._raw_win_start_x + dx)
            self._move_to(nx, ny)

    def _on_raw_button_release(self, button: int, _rx_px: int, _ry_px: int) -> None:
        if not self._raw_dragging or button != self._raw_drag_button:
            return
        self._finish_raw_drag(button)

    def _finish_raw_drag(self, button: int) -> None:
        was_moved = self._raw_drag_moved
        self._raw_dragging = False
        self._raw_drag_button = 0
        self._raw_drag_moved = False
        if was_moved:
            self.config.top_bar_x = self._pos_x
            self.config_service.save()
        elif button == 1:
            self.popup_win.toggle_near(self, self.state_machine, self.config.sound_enabled)

    # --- Floating Mode GTK Handlers ---

    def _on_floating_press(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            self._floating_dragging = False
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._raw_win_start_x, self._pos_y = self.get_position()
            return True
        elif event.button == 3:
            self._show_context_menu(event)
            return True
        return False

    def _on_floating_motion(self, _widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            if not self._floating_dragging and (abs(dx) > 3 or abs(dy) > 3):
                self._floating_dragging = True
            if self._floating_dragging:
                self.move(int(self._raw_win_start_x + dx), int(self._pos_y + dy))
                return True
        return False

    def _on_floating_release(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            if self._floating_dragging:
                self._floating_dragging = False
                cur_x, cur_y = self.get_position()
                self.config_service.update_position(cur_x, cur_y)
            else:
                self.popup_win.toggle_near(self, self.state_machine, self.config.sound_enabled)
            return True
        return False

    def _show_context_menu(self, event: Optional[Gdk.EventButton] = None) -> None:
        menu = Gtk.Menu()

        item_test = Gtk.MenuItem(label='🔔 Test Alert Now')
        item_test.connect('activate', lambda _: self.state_machine.trigger_test_alert())
        menu.append(item_test)

        item_reset = Gtk.MenuItem(label='🔄 Reset Timer')
        item_reset.connect('activate', lambda _: self.state_machine.reset())
        menu.append(item_reset)

        sound_label = '🔇 Mute Audio' if self.config.sound_enabled else '🔊 Unmute Audio'
        item_sound = Gtk.MenuItem(label=sound_label)
        item_sound.connect('activate', lambda _: self._on_toggle_sound())
        menu.append(item_sound)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label='✕ Quit')
        item_quit.connect('activate', lambda _: self._on_quit())
        menu.append(item_quit)

        menu.show_all()
        if event:
            menu.popup_at_pointer(event)
        else:
            menu.popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def _on_quit(self) -> None:
        self.cleanup()
        Gtk.main_quit()

    def _on_destroy(self, _widget: Gtk.Widget) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if hasattr(self, '_timer_id') and self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        if self._x11_monitor is not None:
            self._x11_monitor.stop()
            self._x11_monitor = None
        self.sound_service.stop_ticking()
        self.notification_service.dismiss()
        self.activity_monitor.close()
        if hasattr(self, 'popup_win') and self.popup_win:
            self.popup_win.destroy()
