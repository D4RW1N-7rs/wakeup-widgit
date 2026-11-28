"""Popup detail card window positioned cleanly beneath the top bar pill."""

import time
from typing import Callable, Optional

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

from wake_widget import __version__
from wake_widget.constants import APP_NAME, STATE_ACTIVE, STATE_ALERT, STATE_COUNTDOWN
from wake_widget.core.state_machine import WakeStateMachine
from wake_widget.ui.ring_widget import ProgressRing
from wake_widget.ui.styles import enable_rgba


def format_mmss(seconds: float) -> str:
    sec = max(0, int(seconds))
    return f'{sec // 60:02d}:{sec % 60:02d}'


class PopupWindow(Gtk.Window):
    """Sleek dark popup card displayed when clicking the top bar pill."""

    def __init__(
        self,
        on_test_alert: Callable[[], None],
        on_reset: Callable[[], None],
        on_toggle_sound: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.on_test_alert = on_test_alert
        self.on_reset = on_reset
        self.on_toggle_sound = on_toggle_sound
        self.on_quit = on_quit
        self._opened_at: float = 0.0

        self.get_style_context().add_class('wake-transparent')
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.stick()
        enable_rgba(self)

        self.connect('key-press-event', self._on_key_press)
        self.connect('focus-out-event', self._on_focus_out)

        self._build_ui()

    def _build_ui(self) -> None:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class('wake-card')
        card.set_size_request(300, -1)
        self.add(card)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class('wake-card-header')

        title_lbl = Gtk.Label(label=f'{APP_NAME} v{__version__}')
        title_lbl.get_style_context().add_class('wake-card-title')
        header.pack_start(title_lbl, False, False, 0)

        self.badge = Gtk.Label(label='ACTIVE')
        self.badge.get_style_context().add_class('wake-badge')
        self.badge.get_style_context().add_class('wake-badge-active')
        header.pack_end(self.badge, False, False, 0)
        card.pack_start(header, False, False, 0)

        # Middle: Ring + Monospace Clock
        clock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.ring = ProgressRing(size=36)
        clock_row.pack_start(self.ring, False, False, 4)

        vbox_clock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.lbl_big_clock = Gtk.Label(label='04:00')
        self.lbl_big_clock.set_xalign(0.0)
        self.lbl_big_clock.get_style_context().add_class('wake-big-clock')
        vbox_clock.pack_start(self.lbl_big_clock, False, False, 0)

        self.lbl_desc = Gtk.Label(label='Inactivity gate: 15s • User active')
        self.lbl_desc.set_xalign(0.0)
        self.lbl_desc.get_style_context().add_class('wake-card-desc')
        vbox_clock.pack_start(self.lbl_desc, False, False, 0)

        clock_row.pack_start(vbox_clock, True, True, 0)
        card.pack_start(clock_row, False, False, 4)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.btn_test = Gtk.Button(label='* Test Alert')
        self.btn_test.get_style_context().add_class('wake-btn')
        self.btn_test.get_style_context().add_class('wake-btn-primary')
        self.btn_test.connect('clicked', self._on_btn_test_clicked)
        btn_box.pack_start(self.btn_test, True, True, 0)

        self.btn_reset = Gtk.Button(label='↺ Reset')
        self.btn_reset.get_style_context().add_class('wake-btn')
        self.btn_reset.connect('clicked', self._on_btn_reset_clicked)
        btn_box.pack_start(self.btn_reset, True, True, 0)

        self.btn_sound = Gtk.Button(label='Sound: ON')
        self.btn_sound.get_style_context().add_class('wake-btn')
        self.btn_sound.connect('clicked', self._on_btn_sound_clicked)
        btn_box.pack_start(self.btn_sound, True, True, 0)

        self.btn_close = Gtk.Button(label='x Close')
        self.btn_close.get_style_context().add_class('wake-btn')
        self.btn_close.get_style_context().add_class('wake-btn-danger')
        self.btn_close.connect('clicked', lambda _: self.hide())
        btn_box.pack_start(self.btn_close, False, False, 0)

        card.pack_start(btn_box, False, False, 2)

    def _on_btn_test_clicked(self, _btn: Gtk.Button) -> None:
        self.on_test_alert()

    def _on_btn_reset_clicked(self, _btn: Gtk.Button) -> None:
        self.on_reset()

    def _on_btn_sound_clicked(self, _btn: Gtk.Button) -> None:
        self.on_toggle_sound()

    def update_state(self, sm: WakeStateMachine, sound_enabled: bool) -> None:
        self.ring.set_data(sm.state, sm.countdown_progress)

        # Update badge
        for s in ('active', 'countdown', 'alert'):
            self.badge.get_style_context().remove_class(f'wake-badge-{s}')
        self.badge.get_style_context().add_class(f'wake-badge-{sm.state}')
        self.badge.set_text(sm.state.upper())

        # Update test button label and style
        if sm.is_test_alert_active:
            self.btn_test.set_label('[ ] Stop Test')
            self.btn_test.get_style_context().remove_class('wake-btn-primary')
            self.btn_test.get_style_context().add_class('wake-btn-danger')
        else:
            self.btn_test.set_label('* Test Alert')
            self.btn_test.get_style_context().remove_class('wake-btn-danger')
            self.btn_test.get_style_context().add_class('wake-btn-primary')

        # Update clock
        if sm.is_test_alert_active:
            self.lbl_big_clock.set_text('00:00')
            self.lbl_desc.set_text('* Test alert active! Click "Stop Test" to stop.')
        elif sm.state == STATE_ACTIVE:
            self.lbl_big_clock.set_text(format_mmss(sm.timer_duration_seconds))
            idle_s = int(sm.idle_seconds)
            gate_s = int(sm.idle_delay_seconds)
            self.lbl_desc.set_text(f'Waiting for {gate_s}s idle ({idle_s}s / {gate_s}s)')
        elif sm.state == STATE_COUNTDOWN:
            self.lbl_big_clock.set_text(format_mmss(sm.countdown_remaining))
            self.lbl_desc.set_text('4-min timer running down!')
        else:
            self.lbl_big_clock.set_text('00:00')
            self.lbl_desc.set_text('!! Inactive! Ticking active.')

        self.btn_sound.set_label('Sound: ON' if sound_enabled else 'Sound: OFF')

    def position_near(self, anchor_window: Gtk.Window) -> None:
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo = monitor.get_geometry()
        wa = monitor.get_workarea()
        panel_bottom = wa.y if wa.y > geo.y else geo.y + 28

        if hasattr(anchor_window, 'get_screen_rect'):
            px, py, pw, ph = anchor_window.get_screen_rect()
        else:
            px, py = anchor_window.get_position()
            pw, ph = anchor_window.get_size()

        mw, mh = self.get_size()
        centered_x = px + (pw - mw) // 2
        target_x = max(geo.x + 8, min(centered_x, geo.x + geo.width - mw - 8))
        target_y = max(panel_bottom + 4, py + ph + 6)
        self.move(target_x, target_y)

    def toggle_near(self, anchor_window: Gtk.Window, sm: WakeStateMachine, sound_enabled: bool) -> None:
        if self.get_visible():
            self.hide()
            return
        self.update_state(sm, sound_enabled)
        self._opened_at = time.monotonic()
        self.show_all()
        self.update_state(sm, sound_enabled)
        self.position_near(anchor_window)
        self.present()

    def _on_key_press(self, _widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def _on_focus_out(self, _widget: Gtk.Widget, _event: Gdk.EventFocus) -> bool:
        if not self.get_visible() or (time.monotonic() - getattr(self, '_opened_at', 0.0)) < 0.3:
            return False
        self.hide()
        return False
