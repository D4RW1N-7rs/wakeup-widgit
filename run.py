#!/usr/bin/env python3
"""Entrypoint for Wake Widget - Inactivity detector & 4-minute warning ticking reminder."""

import argparse
import signal
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from wake_widget.config import ConfigService
from wake_widget.constants import (
    DEFAULT_IDLE_DELAY_SECONDS,
    DEFAULT_TIMER_DURATION_SECONDS,
)
from wake_widget.core.activity_monitor import ActivityMonitor
from wake_widget.services.notification_service import NotificationService
from wake_widget.services.sound_service import SoundService
from wake_widget.ui.pill_window import PillWindow
from wake_widget.ui.styles import install_css


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Wake Widget - Desktop inactivity detector & 4-minute ticking alert reminder',
    )
    parser.add_argument(
        '--idle-seconds',
        type=float,
        default=None,
        help=f'Inactivity threshold before countdown starts (default: {DEFAULT_IDLE_DELAY_SECONDS}s)',
    )
    parser.add_argument(
        '--timer-seconds',
        type=float,
        default=None,
        help=f'Countdown timer duration before alert triggers (default: {DEFAULT_TIMER_DURATION_SECONDS}s / 4 minutes)',
    )
    parser.add_argument(
        '--fast-test',
        action='store_true',
        help='Run in fast test mode (3s inactivity -> 5s timer -> alert ticking) for quick demonstration',
    )
    parser.add_argument(
        '--test-alert',
        action='store_true',
        help='Trigger alert ticking sound and notification immediately on startup',
    )
    parser.add_argument(
        '--mute',
        action='store_true',
        help='Start with audio muted',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Allow graceful termination via Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Initialize configuration and services
    config_service = ConfigService()
    if args.idle_seconds is not None:
        config_service.config.idle_delay_seconds = args.idle_seconds
    if args.timer_seconds is not None:
        config_service.config.timer_duration_seconds = args.timer_seconds
    if args.mute:
        config_service.config.sound_enabled = False

    activity_monitor = ActivityMonitor()
    sound_service = SoundService(
        sound_enabled=config_service.config.sound_enabled,
        tick_interval=config_service.config.tick_interval_seconds,
    )
    notification_service = NotificationService(
        enabled=config_service.config.notification_enabled,
    )

    # Install CSS styling
    install_css()

    # Create and display floating pill
    pill = PillWindow(
        config_service=config_service,
        activity_monitor=activity_monitor,
        sound_service=sound_service,
        notification_service=notification_service,
        fast_test=args.fast_test,
        test_alert=args.test_alert,
    )
    pill.show_all()

    try:
        Gtk.main()
    finally:
        pill.cleanup()


if __name__ == '__main__':
    main()
