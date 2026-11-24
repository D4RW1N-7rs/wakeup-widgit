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

        self.is_test_alert_active: bool = False
        self._last_idle_seconds: float = 0.0
        self._alert_start_time: float = 0.0

    def toggle_test_alert(self) -> bool:
        """Toggle test alert mode. Keeps working continuously until clicked again."""
        if self.is_test_alert_active:
            self.stop_test_alert()
            return False
        else:
            self.start_test_alert()
            return True

    def start_test_alert(self) -> None:
        """Starts test alert and keeps it active until explicitly stopped."""
        old_state = self.state
        self.is_test_alert_active = True
        self.state = STATE_ALERT
        self.countdown_remaining = 0.0
        self.countdown_progress = 1.0
        self.gate_progress = 1.0
        self._alert_start_time = time.monotonic()
        if old_state != STATE_ALERT and self.on_alert_triggered:
            self.on_alert_triggered()
        if old_state != STATE_ALERT and self.on_state_changed:
            self.on_state_changed(old_state, STATE_ALERT)

    def stop_test_alert(self) -> None:
        """Stops test alert and returns to normal active tracking."""
        if not self.is_test_alert_active:
            return
        self.is_test_alert_active = False
        self.state = STATE_ACTIVE
        self.countdown_remaining = self.timer_duration_seconds
        self.countdown_progress = 0.0
        self.gate_progress = 0.0
        if self.on_alert_dismissed:
            self.on_alert_dismissed()
        if self.on_state_changed:
            self.on_state_changed(STATE_ALERT, STATE_ACTIVE)

    # Backward compatibility alias
    trigger_test_alert = toggle_test_alert

    def reset(self) -> None:
        """Reset state machine back to start (STATE_ACTIVE)."""
        old_state = self.state
        was_test = self.is_test_alert_active
        self.is_test_alert_active = False
        self.state = STATE_ACTIVE
        self.countdown_remaining = self.timer_duration_seconds
        self.countdown_progress = 0.0
        self.gate_progress = 0.0
        self._last_idle_seconds = 0.0

        if (old_state == STATE_ALERT or was_test) and self.on_alert_dismissed:
            self.on_alert_dismissed()
        if old_state != STATE_ACTIVE and self.on_state_changed:
            self.on_state_changed(old_state, STATE_ACTIVE)

    def update(self, idle_seconds: float) -> str:
        """Update state machine with latest measured idle time in seconds."""
        self.idle_seconds = max(0.0, idle_seconds)
        old_state = self.state

        # 1. If manual test alert is active, it stays active UNTIL clicked again!
        if self.is_test_alert_active:
            self.state = STATE_ALERT
            self.countdown_remaining = 0.0
            self.countdown_progress = 1.0
            self.gate_progress = 1.0
            self._last_idle_seconds = self.idle_seconds
            return self.state

        # 2. Normal monitoring: detect user mouse/keyboard activity
        activity_detected = (
            self.idle_seconds < 0.25
            or (self.idle_seconds + 0.3) < self._last_idle_seconds
        )

        if activity_detected:
            # Dismiss automatic inactivity alert when user returns
            if self.state == STATE_ALERT:
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

        # 3. Inactivity progression
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
