"""Always-on-top draggable floating pill and expanded control card for Wake Widget."""

import math
import os
import sys
import time
from typing import Optional

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib, Gtk

from wake_widget.config import ConfigService
from wake_widget.constants import (
    APP_NAME,
    DEFAULT_IDLE_DELAY_SECONDS,
    DEFAULT_TIMER_DURATION_SECONDS,
    STATE_ACTIVE,
    STATE_ALERT,
    STATE_COUNTDOWN,
)
from wake_widget.core.activity_monitor import ActivityMonitor
from wake_widget.core.state_machine import WakeStateMachine
from wake_widget.services.notification_service import NotificationService
from wake_widget.services.sound_service import SoundService
from wake_widget.ui.ring_widget import ProgressRing
from wake_widget.ui.styles import enable_rgba, install_css


def format_time_mmss(seconds: float) -> str:
    """Format seconds as MM:SS."""
    sec = max(0, int(math.ceil(seconds)))
    m = sec // 60
    s = sec % 60
    return f'{m:02d}:{s:02d}'


class PillWindow(Gtk.Window):
    """Floating desktop pill displaying live activity state and countdown."""

    def __init__(
        self,
        config_service: ConfigService,
        activity_monitor: ActivityMonitor,
        sound_service: SoundService,
        notification_service: NotificationService,
        fast_test: bool = False,
        test_alert: bool = False,
    ) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.config_service = config_service
        self.config = config_service.config
        self.activity_monitor = activity_monitor
        self.sound_service = sound_service
        self.notification_service = notification_service

        idle_delay = 3.0 if fast_test else self.config.idle_delay_seconds
        timer_duration = 5.0 if fast_test else self.config.timer_duration_seconds

        self.state_machine = WakeStateMachine(
            idle_delay_seconds=idle_delay,
            timer_duration_seconds=timer_duration,
            on_state_changed=self._on_state_changed,
            on_alert_triggered=self._on_alert_triggered,
            on_alert_dismissed=self._on_alert_dismissed,
        )

        # Drag tracking
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._window_start_x = 0
        self._window_start_y = 0

        # UI State
        self._card_expanded = False
        self._current_css_state = STATE_ACTIVE

        # Setup window properties
        self.set_title(APP_NAME)
        self.set_decorated(False)
        self.set_keep_above(self.config.always_on_top)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.stick()
        self.get_style_context().add_class('wake-transparent')
        enable_rgba(self)

        # Connect events
        self.connect('button-press-event', self._on_button_press)
        self.connect('button-release-event', self._on_button_release)
        self.connect('motion-notify-event', self._on_motion_notify)
        self.connect('destroy', self._on_destroy)

        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        self._build_ui()
        self._restore_position()

        if test_alert:
            self.state_machine.trigger_test_alert()

        # Start 100ms update loop
        self._timer_id = GLib.timeout_add(100, self._on_tick)

    def _build_ui(self) -> None:
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add(self.main_box)

        # 1. Floating Pill Container
        self.pill_event_box = Gtk.EventBox()
        self.pill_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pill_box.get_style_context().add_class('wake-pill')
        self.pill_box.get_style_context().add_class('wake-state-active')
        self.pill_event_box.add(self.pill_box)
        self.main_box.pack_start(self.pill_event_box, False, False, 0)

        # Pill Left: Progress Ring
        self.pill_ring = ProgressRing(size=20, stroke_width=2.5)
        self.pill_box.pack_start(self.pill_ring, False, False, 0)

        # Pill Center: Label Stack (Title/Clock + Subtitle)
        vbox_labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.lbl_clock = Gtk.Label(label='Active')
        self.lbl_clock.set_xalign(0.0)
        self.lbl_clock.get_style_context().add_class('wake-label-clock')
        vbox_labels.pack_start(self.lbl_clock, False, False, 0)

        self.lbl_sub = Gtk.Label(label='0:00 / 0:15')
        self.lbl_sub.set_xalign(0.0)
        self.lbl_sub.get_style_context().add_class('wake-label-sub')
        vbox_labels.pack_start(self.lbl_sub, False, False, 0)

        self.pill_box.pack_start(vbox_labels, True, True, 2)

        # Pill Right: Mute toggle & Expand arrow
        self.btn_sound_icon = Gtk.Label(label='🔊' if self.config.sound_enabled else '🔇')
        self.pill_box.pack_start(self.btn_sound_icon, False, False, 2)

        self.lbl_expand_icon = Gtk.Label(label='▾')
        self.lbl_expand_icon.get_style_context().add_class('wake-label-sub')
        self.pill_box.pack_start(self.lbl_expand_icon, False, False, 2)

        # 2. Expanded Detail Card (Initially hidden)
        self.card_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.card_container.get_style_context().add_class('wake-card')
        self.card_container.set_no_show_all(True)
        self.main_box.pack_start(self.card_container, False, False, 0)

        self._build_card_ui()

    def _build_card_ui(self) -> None:
        # Card Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.get_style_context().add_class('wake-card-header')

        title_lbl = Gtk.Label(label=APP_NAME)
        title_lbl.get_style_context().add_class('wake-label-title')
        header_box.pack_start(title_lbl, False, False, 0)

        self.badge_state = Gtk.Label(label='ACTIVE')
        self.badge_state.get_style_context().add_class('wake-badge')
        self.badge_state.get_style_context().add_class('wake-badge-active')
        header_box.pack_end(self.badge_state, False, False, 0)
        self.card_container.pack_start(header_box, False, False, 0)

        # Big Digital Clock & Large Ring
        clock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.card_ring = ProgressRing(size=44, stroke_width=4.0)
        clock_row.pack_start(self.card_ring, False, False, 4)

        vbox_clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.card_big_clock = Gtk.Label(label='04:00')
        self.card_big_clock.set_xalign(0.0)
        self.card_big_clock.get_style_context().add_class('wake-big-clock')
        vbox_clock.pack_start(self.card_big_clock, False, False, 0)

        self.card_desc = Gtk.Label(label='Inactivity Gate: User is active')
        self.card_desc.set_xalign(0.0)
        self.card_desc.get_style_context().add_class('wake-card-desc')
        vbox_clock.pack_start(self.card_desc, False, False, 0)

        clock_row.pack_start(vbox_clock, True, True, 0)
        self.card_container.pack_start(clock_row, False, False, 4)

        # Controls Row: [Test Alert] [Reset] [Mute] [Settings]
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_test = Gtk.Button(label='🔔 Test Alert')
        btn_test.get_style_context().add_class('wake-btn')
        btn_test.get_style_context().add_class('wake-btn-primary')
        btn_test.connect('clicked', lambda _: self.state_machine.trigger_test_alert())
        btn_row.pack_start(btn_test, True, True, 0)

        btn_reset = Gtk.Button(label='🔄 Reset')
        btn_reset.get_style_context().add_class('wake-btn')
        btn_reset.connect('clicked', lambda _: self.state_machine.reset())
        btn_row.pack_start(btn_reset, True, True, 0)

        self.btn_sound_toggle = Gtk.Button(label='🔊 Sound: ON' if self.config.sound_enabled else '🔇 Sound: OFF')
        self.btn_sound_toggle.get_style_context().add_class('wake-btn')
        self.btn_sound_toggle.connect('clicked', self._on_toggle_sound)
        btn_row.pack_start(self.btn_sound_toggle, True, True, 0)

        btn_quit = Gtk.Button(label='✕ Close')
        btn_quit.get_style_context().add_class('wake-btn')
        btn_quit.get_style_context().add_class('wake-btn-danger')
        btn_quit.connect('clicked', lambda _: self._on_quit())
        btn_row.pack_start(btn_quit, False, False, 0)

        self.card_container.pack_start(btn_row, False, False, 4)

    def _restore_position(self) -> None:
        screen = self.get_screen()
        w = screen.get_width()
        x = self.config.widget_x if self.config.widget_x is not None else max(10, w - 240)
        y = self.config.widget_y if self.config.widget_y is not None else 32
        self.move(x, y)

    def _on_tick(self) -> bool:
        idle_seconds = self.activity_monitor.get_idle_seconds()
        state = self.state_machine.update(idle_seconds)

        # Update visuals according to state
        if state == STATE_ACTIVE:
            self.lbl_clock.set_text('Active')
            idle_display = format_time_mmss(self.state_machine.idle_seconds)
            gate_target = format_time_mmss(self.state_machine.idle_delay_seconds)
            self.lbl_sub.set_text(f'Idle: {idle_display} / {gate_target}')
            self.pill_ring.set_data(STATE_ACTIVE, 0.0)

            if self._card_expanded:
                self.card_big_clock.set_text(format_time_mmss(self.state_machine.timer_duration_seconds))
                self.card_desc.set_text(f'Activity detected. Waiting for {int(self.state_machine.idle_delay_seconds)}s idle...')
                self.card_ring.set_data(STATE_ACTIVE, 0.0)

        elif state == STATE_COUNTDOWN:
            remaining_str = format_time_mmss(self.state_machine.countdown_remaining)
            self.lbl_clock.set_text(f'⏳ {remaining_str}')
            self.lbl_sub.set_text('4-Min Inactivity Timer')
            self.pill_ring.set_data(STATE_COUNTDOWN, self.state_machine.countdown_progress)

            if self._card_expanded:
                self.card_big_clock.set_text(remaining_str)
                self.card_desc.set_text('User inactive > 15s. Timer ticking down!')
                self.card_ring.set_data(STATE_COUNTDOWN, self.state_machine.countdown_progress)

        elif state == STATE_ALERT:
            self.lbl_clock.set_text('🔔 WAKE UP!')
            self.lbl_sub.set_text('Move mouse / type!')
            self.pill_ring.set_data(STATE_ALERT, 1.0)

            if self._card_expanded:
                self.card_big_clock.set_text('00:00')
                self.card_desc.set_text('⏰ Timer expired! Ticking active until you interact.')
                self.card_ring.set_data(STATE_ALERT, 1.0)

        return True

    def _on_state_changed(self, old_state: str, new_state: str) -> None:
        style_context = self.pill_box.get_style_context()
        style_context.remove_class(f'wake-state-{old_state}')
        style_context.add_class(f'wake-state-{new_state}')

        self.badge_state.get_style_context().remove_class(f'wake-badge-{old_state}')
        self.badge_state.get_style_context().add_class(f'wake-badge-{new_state}')
        self.badge_state.set_text(new_state.upper())

    def _on_alert_triggered(self) -> None:
        if self.config.sound_enabled:
            self.sound_service.start_ticking()
        if self.config.notification_enabled:
            timer_m = int(self.state_machine.timer_duration_seconds // 60)
            self.notification_service.show_alert(
                title='⏰ Inactivity Warning!',
                body=f'{timer_m} minutes without activity. Move mouse or press any key!',
            )

    def _on_alert_dismissed(self) -> None:
        self.sound_service.stop_ticking()
        self.notification_service.dismiss()

    def _on_toggle_sound(self, _widget: Optional[Gtk.Widget] = None) -> None:
        self.config.sound_enabled = not self.config.sound_enabled
        self.sound_service.sound_enabled = self.config.sound_enabled
        icon = '🔊' if self.config.sound_enabled else '🔇'
        self.btn_sound_icon.set_text(icon)
        self.btn_sound_toggle.set_label(f'{icon} Sound: {"ON" if self.config.sound_enabled else "OFF"}')
        self.config_service.save()
        if not self.config.sound_enabled:
            self.sound_service.stop_ticking()

    def _toggle_card(self) -> None:
        self._card_expanded = not self._card_expanded
        self.lbl_expand_icon.set_text('▴' if self._card_expanded else '▾')
        if self._card_expanded:
            self.card_container.show_all()
        else:
            self.card_container.hide()
        self.resize(1, 1)

    def _on_button_press(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            # Left click -> initiate potential drag
            self._dragging = False
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            wx, wy = self.get_position()
            self._window_start_x = wx
            self._window_start_y = wy
            return True
        elif event.button == 3:
            # Right click -> Context menu
            self._show_context_menu(event)
            return True
        return False

    def _on_motion_notify(self, _widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            if not self._dragging and (abs(dx) > 3 or abs(dy) > 3):
                self._dragging = True
            if self._dragging:
                self.move(int(self._window_start_x + dx), int(self._window_start_y + dy))
                return True
        return False

    def _on_button_release(self, _widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            if self._dragging:
                self._dragging = False
                cur_x, cur_y = self.get_position()
                self.config_service.update_position(cur_x, cur_y)
            else:
                # Normal click without drag -> toggle detail card
                self._toggle_card()
            return True
        return False

    def _show_context_menu(self, event: Gdk.EventButton) -> None:
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
        menu.popup_at_pointer(event)

    def _on_quit(self) -> None:
        self.cleanup()
        Gtk.main_quit()

    def _on_destroy(self, _widget: Gtk.Widget) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if hasattr(self, '_timer_id') and self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self.sound_service.stop_ticking()
        self.notification_service.dismiss()
        self.activity_monitor.close()
