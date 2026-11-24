"""Unit tests for Wake Widget components and state transitions."""

import os
import unittest

from wake_widget.config import WidgetConfig
from wake_widget.constants import (
    CHIME_SOUND_PATH,
    STATE_ACTIVE,
    STATE_ALERT,
    STATE_COUNTDOWN,
    TICK_SOUND_PATH,
    TOCK_SOUND_PATH,
)
from wake_widget.core.activity_monitor import ActivityMonitor
from wake_widget.core.state_machine import WakeStateMachine
from wake_widget.services.sound_service import SoundService, ensure_sound_assets
from wake_widget.ui.pill_window import format_time_mmss


class TestWakeWidget(unittest.TestCase):
    def setUp(self) -> None:
        self.state_changes = []
        self.alert_triggered_count = 0
        self.alert_dismissed_count = 0
        self.activity_detected_count = 0

        self.sm = WakeStateMachine(
            idle_delay_seconds=15.0,
            timer_duration_seconds=240.0,
            on_state_changed=lambda old, new: self.state_changes.append((old, new)),
            on_alert_triggered=self._on_alert_triggered,
            on_alert_dismissed=self._on_alert_dismissed,
            on_activity_detected=self._on_activity_detected,
        )

    def _on_alert_triggered(self) -> None:
        self.alert_triggered_count += 1

    def _on_alert_dismissed(self) -> None:
        self.alert_dismissed_count += 1

    def _on_activity_detected(self) -> None:
        self.activity_detected_count += 1

    def test_state_active_while_idle_under_15s(self) -> None:
        """User inactive for < 15s keeps state in ACTIVE without starting countdown."""
        self.assertEqual(self.sm.update(0.0), STATE_ACTIVE)
        self.assertEqual(self.sm.update(5.0), STATE_ACTIVE)
        self.assertEqual(self.sm.update(14.9), STATE_ACTIVE)
        self.assertEqual(self.sm.countdown_remaining, 240.0)
        self.assertEqual(self.alert_triggered_count, 0)

    def test_state_countdown_starts_after_15s(self) -> None:
        """Inactivity of 15s starts 4-minute timer counting down."""
        # Step through to 15s
        self.sm.update(5.0)
        self.sm.update(15.0)
        self.assertEqual(self.sm.state, STATE_COUNTDOWN)
        self.assertAlmostEqual(self.sm.countdown_remaining, 240.0, delta=0.1)

        # Inactive for 75s (15s idle + 60s in timer)
        self.sm.update(75.0)
        self.assertEqual(self.sm.state, STATE_COUNTDOWN)
        self.assertAlmostEqual(self.sm.countdown_remaining, 180.0, delta=0.1)

        # Inactive for 254s (1s left of 4-min timer)
        self.sm.update(254.0)
        self.assertEqual(self.sm.state, STATE_COUNTDOWN)
        self.assertAlmostEqual(self.sm.countdown_remaining, 1.0, delta=0.1)
        self.assertEqual(self.alert_triggered_count, 0)

    def test_alert_triggers_when_4min_is_hit(self) -> None:
        """Inactivity of 255s (15s + 240s) triggers ALERT and callback."""
        self.sm.update(254.9)
        self.assertEqual(self.sm.state, STATE_COUNTDOWN)

        # 4 minutes reached!
        self.sm.update(255.0)
        self.assertEqual(self.sm.state, STATE_ALERT)
        self.assertEqual(self.alert_triggered_count, 1)
        self.assertEqual(self.sm.countdown_remaining, 0.0)

    def test_activity_resets_cycle_from_countdown(self) -> None:
        """Moving mouse or typing during countdown immediately resets to start."""
        self.sm.update(100.0)  # In countdown
        self.assertEqual(self.sm.state, STATE_COUNTDOWN)

        # User moves mouse / clicks -> idle drops to 0.05s
        self.sm.update(0.05)
        self.assertEqual(self.sm.state, STATE_ACTIVE)
        self.assertEqual(self.sm.countdown_remaining, 240.0)
        self.assertGreaterEqual(self.activity_detected_count, 1)

    def test_activity_resets_cycle_from_alert(self) -> None:
        """Moving mouse or typing while alert is ticking dismisses alert and resets."""
        self.sm.update(260.0)
        self.assertEqual(self.sm.state, STATE_ALERT)
        self.assertEqual(self.alert_triggered_count, 1)

        # User presses keyboard key -> idle drops
        self.sm.update(0.1)
        self.assertEqual(self.sm.state, STATE_ACTIVE)
        self.assertEqual(self.alert_dismissed_count, 1)
        self.assertEqual(self.sm.countdown_remaining, 240.0)

    def test_manual_test_alert_and_reset(self) -> None:
        """Manual test alert triggers immediately and clears on activity."""
        self.sm.trigger_test_alert()
        self.assertEqual(self.sm.state, STATE_ALERT)
        self.assertEqual(self.alert_triggered_count, 1)

        # Activity clears test alert
        self.sm.update(0.0)
        self.assertEqual(self.sm.state, STATE_ACTIVE)
        self.assertEqual(self.alert_dismissed_count, 1)

    def test_format_time_mmss(self) -> None:
        """MM:SS formatting verification."""
        self.assertEqual(format_time_mmss(240.0), '04:00')
        self.assertEqual(format_time_mmss(59.0), '00:59')
        self.assertEqual(format_time_mmss(0.0), '00:00')
        self.assertEqual(format_time_mmss(65.0), '01:05')

    def test_activity_monitor_loads(self) -> None:
        """ActivityMonitor initializes and returns non-negative idle float."""
        monitor = ActivityMonitor()
        idle = monitor.get_idle_seconds()
        self.assertIsInstance(idle, float)
        self.assertGreaterEqual(idle, 0.0)
        monitor.close()

    def test_sound_assets_exist(self) -> None:
        """Sound assets (tick, tock, chime) exist and are valid wav files."""
        ensure_sound_assets()
        for path in (TICK_SOUND_PATH, TOCK_SOUND_PATH, CHIME_SOUND_PATH):
            self.assertTrue(os.path.isfile(path), f'Missing {path}')
            self.assertGreater(os.path.getsize(path), 100)

    def test_sound_service_start_stop(self) -> None:
        """Sound service ticking thread starts and stops gracefully without blocking."""
        sound_srv = SoundService(sound_enabled=False)
        sound_srv.start_ticking()
        self.assertTrue(sound_srv._is_ticking)
        sound_srv.stop_ticking()
        self.assertFalse(sound_srv._is_ticking)

    def test_config_serialization(self) -> None:
        """Configuration roundtrip check."""
        cfg = WidgetConfig(
            idle_delay_seconds=15.0,
            timer_duration_seconds=240.0,
            sound_enabled=True,
            widget_x=120,
            widget_y=80,
        )
        d = cfg.to_dict()
        restored = WidgetConfig.from_dict(d)
        self.assertEqual(restored.idle_delay_seconds, 15.0)
        self.assertEqual(restored.timer_duration_seconds, 240.0)
        self.assertEqual(restored.widget_x, 120)
        self.assertEqual(restored.widget_y, 80)


if __name__ == '__main__':
    unittest.main()
