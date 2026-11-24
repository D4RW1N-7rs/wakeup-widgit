"""State machine managing inactivity detection, 4-minute countdown, and alert ticking."""

import time
from typing import Callable, Optional

from wake_widget.constants import (
    DEFAULT_IDLE_DELAY_SECONDS,
    DEFAULT_TIMER_DURATION_SECONDS,
    STATE_ACTIVE,
    STATE_ALERT,
    STATE_COUNTDOWN,
)


class WakeStateMachine:
    """Implements the inactivity -> 4-min timer -> ticking alert -> reset cycle."""

    def __init__(
        self,
        idle_delay_seconds: float = DEFAULT_IDLE_DELAY_SECONDS,
        timer_duration_seconds: float = DEFAULT_TIMER_DURATION_SECONDS,
        on_state_changed: Optional[Callable[[str, str], None]] = None,
        on_alert_triggered: Optional[Callable[[], None]] = None,
        on_alert_dismissed: Optional[Callable[[], None]] = None,
        on_activity_detected: Optional[Callable[[], None]] = None,
    ) -> None:
        self.idle_delay_seconds = idle_delay_seconds
        self.timer_duration_seconds = timer_duration_seconds

        self.on_state_changed = on_state_changed
        self.on_alert_triggered = on_alert_triggered
        self.on_alert_dismissed = on_alert_dismissed
        self.on_activity_detected = on_activity_detected

        self.state: str = STATE_ACTIVE
        self.idle_seconds: float = 0.0
        self.countdown_remaining: float = timer_duration_seconds
        self.countdown_progress: float = 0.0
        self.gate_progress: float = 0.0

        self._last_idle_seconds: float = 0.0
        self._force_alert: bool = False
        self._alert_start_time: float = 0.0

    def trigger_test_alert(self) -> None:
        """Manually trigger alert state for testing sounds and notifications."""
        old_state = self.state
        self._force_alert = True
        self.state = STATE_ALERT
        self.countdown_remaining = 0.0
        self.countdown_progress = 1.0
        self.gate_progress = 1.0
        self._alert_start_time = time.monotonic()
        if old_state != STATE_ALERT and self.on_alert_triggered:
            self.on_alert_triggered()
        if old_state != self.state and self.on_state_changed:
            self.on_state_changed(old_state, self.state)

    def reset(self) -> None:
        """Reset state machine back to start (STATE_ACTIVE)."""
        old_state = self.state
        if old_state == STATE_ALERT and self.on_alert_dismissed:
            self.on_alert_dismissed()
        self._force_alert = False
        self.state = STATE_ACTIVE
        self.countdown_remaining = self.timer_duration_seconds
        self.countdown_progress = 0.0
        self.gate_progress = 0.0
        self._last_idle_seconds = 0.0
        if old_state != STATE_ACTIVE and self.on_state_changed:
            self.on_state_changed(old_state, STATE_ACTIVE)

    def update(self, idle_seconds: float) -> str:
        """Update state machine with latest measured idle time in seconds.

        Returns the current state.
        """
        self.idle_seconds = max(0.0, idle_seconds)
        old_state = self.state

        # User activity detected if idle dropped significantly or is near 0
        activity_detected = (
            self.idle_seconds < 0.25
            or (self.idle_seconds + 0.3) < self._last_idle_seconds
        )

        if activity_detected:
            # If user was in test alert or normal alert, dismiss it
            if self.state == STATE_ALERT or self._force_alert:
                self._force_alert = False
                if self.on_alert_dismissed:
                    self.on_alert_dismissed()
            if self.on_activity_detected:
                self.on_activity_detected()

            self.state = STATE_ACTIVE
            self.countdown_remaining = self.timer_duration_seconds
            self.countdown_progress = 0.0
            self.gate_progress = min(1.0, self.idle_seconds / self.idle_delay_seconds)
            self._last_idle_seconds = self.idle_seconds

            if old_state != STATE_ACTIVE and self.on_state_changed:
                self.on_state_changed(old_state, STATE_ACTIVE)
            return self.state

        # If forced alert is active, remain in alert until user activity
        if self._force_alert:
            self.state = STATE_ALERT
            self.countdown_remaining = 0.0
            self.countdown_progress = 1.0
            self.gate_progress = 1.0
            self._last_idle_seconds = self.idle_seconds
            return self.state

        # Determine state based on idle progression
        if self.idle_seconds < self.idle_delay_seconds:
            # Stage 1: Active / Inactivity grace period (does nothing until 15s)
            self.state = STATE_ACTIVE
            self.countdown_remaining = self.timer_duration_seconds
            self.countdown_progress = 0.0
            self.gate_progress = self.idle_seconds / self.idle_delay_seconds
        elif self.idle_seconds < (self.idle_delay_seconds + self.timer_duration_seconds):
            # Stage 2: 4-minute timer running
            self.state = STATE_COUNTDOWN
            elapsed = self.idle_seconds - self.idle_delay_seconds
            self.countdown_remaining = max(0.0, self.timer_duration_seconds - elapsed)
            self.countdown_progress = min(1.0, elapsed / self.timer_duration_seconds)
            self.gate_progress = 1.0
        else:
            # Stage 3: 4 minutes expired -> Alert & ticking sound!
            self.state = STATE_ALERT
            self.countdown_remaining = 0.0
            self.countdown_progress = 1.0
            self.gate_progress = 1.0
            if old_state != STATE_ALERT:
                self._alert_start_time = time.monotonic()
                if self.on_alert_triggered:
                    self.on_alert_triggered()

        if old_state != self.state and self.on_state_changed:
            self.on_state_changed(old_state, self.state)

        self._last_idle_seconds = self.idle_seconds
        return self.state
