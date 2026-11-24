"""GTK3 CSS styling and visual helpers for Wake Widget."""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

WIDGET_CSS = b"""
/* Glassmorphism base window */
.wake-transparent {
    background-color: transparent;
}

/* Floating pill */
.wake-pill {
    background-color: rgba(20, 23, 31, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 4px 12px;
}

.wake-pill:hover {
    border-color: rgba(255, 255, 255, 0.22);
    background-color: rgba(25, 29, 39, 0.97);
}

/* State-specific borders and glows */
.wake-state-active {
    border-color: rgba(34, 197, 94, 0.45);
}

.wake-state-countdown {
    border-color: rgba(245, 158, 11, 0.65);
}

.wake-state-alert {
    border-color: rgba(239, 68, 68, 0.85);
    background-color: rgba(36, 16, 18, 0.96);
}

/* Typography */
.wake-label-title {
    color: #e2e8f0;
    font-size: 11px;
    font-weight: 700;
}

.wake-label-clock {
    color: #ffffff;
    font-size: 13px;
    font-weight: 800;
}

.wake-label-sub {
    color: #94a3b8;
    font-size: 10px;
    font-weight: 500;
}

/* Expanded Card */
.wake-card {
    background-color: rgba(18, 21, 28, 0.97);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 14px;
    padding: 14px;
}

.wake-card-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 8px;
    margin-bottom: 10px;
}

.wake-big-clock {
    color: #f8fafc;
    font-size: 32px;
    font-weight: 800;
}

.wake-card-desc {
    color: #94a3b8;
    font-size: 11px;
}

/* Action Buttons */
.wake-btn {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: #e2e8f0;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
}

.wake-btn:hover {
    background-color: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.25);
    color: #ffffff;
}

.wake-btn-primary {
    background-color: rgba(56, 189, 248, 0.2);
    border-color: rgba(56, 189, 248, 0.5);
    color: #38bdf8;
}

.wake-btn-primary:hover {
    background-color: rgba(56, 189, 248, 0.35);
    color: #ffffff;
}

.wake-btn-danger {
    background-color: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.5);
    color: #f87171;
}

.wake-btn-danger:hover {
    background-color: rgba(239, 68, 68, 0.35);
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
    """Installs custom styling into the GTK default screen provider."""
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
    """Enables RGBA transparency on the window."""
    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual and screen.is_composited():
        window.set_visual(visual)
    window.set_app_paintable(True)
