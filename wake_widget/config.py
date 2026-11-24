"""Configuration model and persistent JSON storage for Wake Widget."""

from dataclasses import dataclass, field
import json
import os
from typing import Optional

from wake_widget.constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_IDLE_DELAY_SECONDS,
    DEFAULT_TICK_INTERVAL_SECONDS,
    DEFAULT_TIMER_DURATION_SECONDS,
)


@dataclass
class WidgetConfig:
    idle_delay_seconds: float = DEFAULT_IDLE_DELAY_SECONDS
    timer_duration_seconds: float = DEFAULT_TIMER_DURATION_SECONDS
    tick_interval_seconds: float = DEFAULT_TICK_INTERVAL_SECONDS
    sound_enabled: bool = True
    notification_enabled: bool = True
    widget_x: Optional[int] = None
    widget_y: Optional[int] = None
    always_on_top: bool = True

    def to_dict(self) -> dict:
        return {
            'idleDelaySeconds': self.idle_delay_seconds,
            'timerDurationSeconds': self.timer_duration_seconds,
            'tickIntervalSeconds': self.tick_interval_seconds,
            'soundEnabled': self.sound_enabled,
            'notificationEnabled': self.notification_enabled,
            'widgetX': self.widget_x,
            'widgetY': self.widget_y,
            'alwaysOnTop': self.always_on_top,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WidgetConfig':
        try:
            idle_s = float(data.get('idleDelaySeconds', DEFAULT_IDLE_DELAY_SECONDS))
        except (TypeError, ValueError):
            idle_s = DEFAULT_IDLE_DELAY_SECONDS
        idle_s = max(1.0, min(3600.0, idle_s))

        try:
            timer_s = float(data.get('timerDurationSeconds', DEFAULT_TIMER_DURATION_SECONDS))
        except (TypeError, ValueError):
            timer_s = DEFAULT_TIMER_DURATION_SECONDS
        timer_s = max(2.0, min(86400.0, timer_s))

        try:
            tick_s = float(data.get('tickIntervalSeconds', DEFAULT_TICK_INTERVAL_SECONDS))
        except (TypeError, ValueError):
            tick_s = DEFAULT_TICK_INTERVAL_SECONDS
        tick_s = max(0.1, min(10.0, tick_s))

        return cls(
            idle_delay_seconds=idle_s,
            timer_duration_seconds=timer_s,
            tick_interval_seconds=tick_s,
            sound_enabled=bool(data.get('soundEnabled', True)),
            notification_enabled=bool(data.get('notificationEnabled', True)),
            widget_x=data.get('widgetX'),
            widget_y=data.get('widgetY'),
            always_on_top=bool(data.get('alwaysOnTop', True)),
        )


class ConfigService:
    def __init__(self, config_path: str = CONFIG_FILE) -> None:
        self.config_path = config_path
        self.config = self.load()

    def load(self) -> WidgetConfig:
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return WidgetConfig.from_dict(data)
            except Exception:
                pass
        return WidgetConfig()

    def save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception:
            pass

    def update_position(self, x: int, y: int) -> None:
        if self.config.widget_x != x or self.config.widget_y != y:
            self.config.widget_x = x
            self.config.widget_y = y
            self.save()
