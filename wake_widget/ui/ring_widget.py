"""Cairo-rendered circular progress ring matching Xattendo top bar aesthetic."""

import math
from typing import Tuple

import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from wake_widget.constants import STATE_ACTIVE, STATE_ALERT, STATE_COUNTDOWN


class ProgressRing(Gtk.DrawingArea):
    """Circular progress ring with center dot and smooth Cairo drawing."""

    def __init__(self, size: int = 16) -> None:
        super().__init__()
        self._size = size
        self._fraction = 0.0
        self._state = STATE_ACTIVE
        self._pulse_alpha = 1.0
        self._pulse_dir = -0.06

        self.set_size_request(size, size)
        self.connect('draw', self._on_draw)

    def set_data(self, state: str, fraction: float) -> None:
        changed = False
        norm_state = state if state in (STATE_ACTIVE, STATE_COUNTDOWN, STATE_ALERT) else STATE_ACTIVE
        if norm_state != self._state:
            self._state = norm_state
            changed = True

        clamped = max(0.0, min(1.0, float(fraction)))
        if abs(clamped - self._fraction) >= 0.005:
            self._fraction = clamped
            changed = True

        if self._state == STATE_ALERT:
            self._pulse_alpha += self._pulse_dir
            if self._pulse_alpha <= 0.35:
                self._pulse_alpha = 0.35
                self._pulse_dir = 0.08
            elif self._pulse_alpha >= 1.0:
                self._pulse_alpha = 1.0
                self._pulse_dir = -0.08
            changed = True
        else:
            self._pulse_alpha = 1.0

        if changed:
            self.queue_draw()

    def _on_draw(self, _widget: Gtk.Widget, ctx: cairo.Context) -> bool:
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        dim = min(w, h)
        if dim <= 2:
            return False

        cx = w / 2.0
        cy = h / 2.0
        stroke_w = max(1.8, dim * 0.13)
        radius = (dim / 2.0) - stroke_w

        ctx.set_antialias(cairo.ANTIALIAS_BEST)

        # Track circle
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.20)
        ctx.set_line_width(stroke_w)
        ctx.arc(cx, cy, radius, 0, 2.0 * math.pi)
        ctx.stroke()

        if self._state == STATE_ACTIVE:
            # Active green #3fb950 or sky blue #38bdf8
            r, g, b = (0.247, 0.725, 0.314)
            ctx.set_source_rgb(r, g, b)
            ctx.set_line_width(stroke_w)
            ctx.arc(cx, cy, radius, 0, 2.0 * math.pi)
            ctx.stroke()

            # Center dot
            ctx.arc(cx, cy, max(1.8, dim * 0.14), 0, 2.0 * math.pi)
            ctx.fill()

        elif self._state == STATE_COUNTDOWN:
            # Amber #d29922 progress arc (starts at 12 o'clock, counts down)
            r, g, b = (0.824, 0.600, 0.133)
            remaining_fraction = max(0.02, 1.0 - self._fraction)
            start_angle = -math.pi / 2.0
            end_angle = start_angle + remaining_fraction * 2.0 * math.pi

            ctx.set_source_rgb(r, g, b)
            ctx.set_line_width(stroke_w)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.arc(cx, cy, radius, start_angle, end_angle)
            ctx.stroke()

            # Center dot
            ctx.arc(cx, cy, max(1.8, dim * 0.14), 0, 2.0 * math.pi)
            ctx.fill()

        else:
            # Alert Ruby Red #ef4444 pulsing
            r, g, b = (0.937, 0.267, 0.267)
            ctx.set_source_rgba(r, g, b, self._pulse_alpha)
            ctx.set_line_width(stroke_w)
            ctx.arc(cx, cy, radius, 0, 2.0 * math.pi)
            ctx.stroke()

            # Pulsing center dot
            ctx.arc(cx, cy, max(1.8, dim * 0.14), 0, 2.0 * math.pi)
            ctx.fill()

        return False
