"""Application constants, file paths, and default timings for Wake Widget."""

import os
from pathlib import Path

APP_NAME = 'Wake Widget'
APP_ID = 'ma.1337.wake-widget'

# Core timings requested by user
# 1. User inactive for 15 seconds -> starts 4-minute timer
DEFAULT_IDLE_DELAY_SECONDS = 15.0
# 2. 4-minute timer -> 240 seconds
DEFAULT_TIMER_DURATION_SECONDS = 240.0
# Ticking rate during alert (1 second tick-tock)
DEFAULT_TICK_INTERVAL_SECONDS = 1.0

# State definitions
STATE_ACTIVE = 'active'
STATE_COUNTDOWN = 'countdown'
STATE_ALERT = 'alert'

# Paths
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
ASSETS_DIR = os.path.join(PROJECT_DIR, 'assets')

TICK_SOUND_PATH = os.path.join(ASSETS_DIR, 'tick.wav')
TOCK_SOUND_PATH = os.path.join(ASSETS_DIR, 'tock.wav')
CHIME_SOUND_PATH = os.path.join(ASSETS_DIR, 'chime.wav')
ICON_SVG_PATH = os.path.join(ASSETS_DIR, 'icon.svg')
ALERT_SVG_PATH = os.path.join(ASSETS_DIR, 'alert.svg')

# Configuration directory in user home
CONFIG_DIR = os.path.expanduser('~/.config/wake-widget')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
