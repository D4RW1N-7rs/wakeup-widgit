"""GTK3 CSS styling matching Xattendo Top Bar Widget styling."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

WIDGET_CSS = b"""
/* Transparency */
window.wake-transparent {
    background-color: transparent;
}

/* Base Top-Bar Pill */
.wake-pill {
    background-color: #1f2226;
    border: 1px solid #32373d;
    border-radius: 999px;
    padding: 2px 11px;
    color: #f0f6fc;
}

.wake-pill:hover,
.wake-pill.wake-pill-hover {
    background-color: #282c31;
    border-color: #38bdf8;
}

/* State: Active (Green accent on hover) */
.wake-pill.state-active {
    border-color: #32373d;
}

.wake-pill.state-active:hover,
.wake-pill.state-active.wake-pill-hover {
    border-color: #38bdf8;
}

/* State: Countdown (Amber Warning) */
.wake-pill.state-countdown {
    background-color: #21190c;
    border: 1px solid #d29922;
}

.wake-pill.state-countdown:hover,
.wake-pill.state-countdown.wake-pill-hover {
    background-color: #2d2210;
    border-color: #e3b341;
}

/* State: Alert (Ruby Red Warning) */
.wake-pill.state-alert {
    background-color: #2a1215;
    border: 1px solid #f87171;
}

.wake-pill.state-alert:hover,
.wake-pill.state-alert.wake-pill-hover {
    background-color: #38181c;
    border-color: #ef4444;
}

/* Pill Monospace Time Label */
.wake-pill-time {
    font-family: "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", monospace;
    font-weight: 700;
    font-size: 11.5px;
    color: #f0f6fc;
}

.wake-pill.state-countdown .wake-pill-time {
    color: #fbbf24;
}

.wake-pill.state-alert .wake-pill-time {
    color: #f87171;
}

/* Popup & Card Surfaces */
.wake-popup-window {
    background-color: transparent;
}

.wake-card {
    background-color: #10151c;
    border: 1px solid #24303e;
    border-radius: 16px;
    padding: 14px;
    color: #e8eef5;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.7);
}

.wake-card-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 8px;
    margin-bottom: 10px;
}

.wake-card-title {
    color: #38bdf8;
    font-size: 12px;
    font-weight: 700;
}

.wake-big-clock {
    color: #f8fafc;
    font-size: 28px;
    font-weight: 800;
    font-family: "JetBrains Mono", "Ubuntu Mono", "DejaVu Sans Mono", monospace;
}

.wake-card-desc {
    color: #94a3b8;
    font-size: 11px;
}

/* Buttons */
.wake-btn {
    background-color: #1c2128;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
}

.wake-btn:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}

.wake-btn-primary {
    background-color: rgba(56, 189, 248, 0.15);
    border-color: rgba(56, 189, 248, 0.4);
    color: #38bdf8;
}

.wake-btn-primary:hover {
    background-color: rgba(56, 189, 248, 0.3);
    color: #ffffff;
}

.wake-btn-danger {
    background-color: rgba(239, 68, 68, 0.15);
    border-color: rgba(239, 68, 68, 0.4);
    color: #f87171;
}

.wake-btn-danger:hover {
    background-color: rgba(239, 68, 68, 0.3);
    color: #ffffff;
}

.wake-badge {
    border-radius: 10px;
    padding: 2px 7px;
    font-size: 9px;
    font-weight: 700;
}

.wake-badge-active {
    background-color: rgba(34, 197, 94, 0.2);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.4);
}

.wake-badge-countdown {
    background-color: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
}

.wake-badge-alert {
    background-color: rgba(239, 68, 68, 0.25);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.5);
}
"""


def install_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(WIDGET_CSS)
    screen = Gdk.Screen.get_default()
    if screen:
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def enable_rgba(window: Gtk.Window) -> None:
    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual and screen.is_composited():
        window.set_visual(visual)
    window.set_app_paintable(True)
