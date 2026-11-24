"""Cairo-drawn circular progress ring and status indicators."""

import math
from typing import Tuple

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from wake_widget.constants import STATE_ACTIVE, STATE_ALERT, STATE_COUNTDOWN


class ProgressRing(Gtk.DrawingArea):
    """Custom circular ring widget rendering state, countdown progress, and pulse glow."""

    def __init__(self, size: int = 24, stroke_width: float = 2.5) -> None:
        super().__init__()
        self.size = size
        self.stroke_width = stroke_width
        self.set_size_request(size, size)

        self._state: str = STATE_ACTIVE
        self._progress: float = 0.0  # 0.0 (full/start) to 1.0 (empty/finished)
        self._pulse_alpha: float = 1.0
        self._pulse_dir: float = -0.05

        self.connect('draw', self._on_draw)

    def set_data(self, state: str, progress: float) -> None:
        changed = False
        if self._state != state:
            self._state = state
            changed = True
        progress = max(0.0, min(1.0, progress))
        if abs(self._progress - progress) > 0.005:
            self._progress = progress
            changed = True

        # Pulse animation when in alert
        if state == STATE_ALERT:
            self._pulse_alpha += self._pulse_dir
            if self._pulse_alpha <= 0.3:
                self._pulse_alpha = 0.3
                self._pulse_dir = 0.08
            elif self._pulse_alpha >= 1.0:
                self._pulse_alpha = 1.0
                self._pulse_dir = -0.08
            changed = True
        else:
            self._pulse_alpha = 1.0

        if changed:
            self.queue_draw()

    def _get_colors(self) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        if self._state == STATE_ACTIVE:
            # Calm Emerald Green
            return (0.13, 0.77, 0.37), (0.1, 0.25, 0.15)
        elif self._state == STATE_COUNTDOWN:
            # Warning Amber
            return (0.96, 0.62, 0.04), (0.3, 0.2, 0.08)
        else:
            # Urgent Ruby Red
            return (0.94, 0.27, 0.27), (0.35, 0.1, 0.1)

    def _on_draw(self, _widget: Gtk.Widget, cr: cairo.Context) -> bool:
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        cx = width / 2.0
        cy = height / 2.0
        radius = min(width, height) / 2.0 - self.stroke_width

        fg, bg = self._get_colors()

        # Background track
        cr.set_line_width(self.stroke_width)
        cr.set_source_rgba(bg[0], bg[1], bg[2], 0.6)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()

        if self._state == STATE_ACTIVE:
            # In active: filled center dot
            cr.set_source_rgba(fg[0], fg[1], fg[2], 0.9)
            cr.arc(cx, cy, radius * 0.45, 0, 2 * math.pi)
            cr.fill()
        elif self._state == STATE_COUNTDOWN:
            # In countdown: arc representing remaining time
            # progress goes 0.0 -> 1.0 as time elapses, so remaining is (1.0 - progress)
            remaining_fraction = 1.0 - self._progress
            start_angle = -math.pi / 2.0
            end_angle = start_angle + (2 * math.pi * remaining_fraction)

            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_source_rgba(fg[0], fg[1], fg[2], 0.95)
            cr.arc(cx, cy, radius, start_angle, end_angle)
            cr.stroke()
        else:
            # In alert: pulsing filled alert circle
            cr.set_source_rgba(fg[0], fg[1], fg[2], self._pulse_alpha * 0.85)
            cr.arc(cx, cy, radius * 0.6, 0, 2 * math.pi)
            cr.fill()

            # Outer ring pulse
            cr.set_line_width(self.stroke_width * 1.2)
            cr.set_source_rgba(fg[0], fg[1], fg[2], self._pulse_alpha)
            cr.arc(cx, cy, radius, 0, 2 * math.pi)
            cr.stroke()

        return True
