"""Audio engine for clock ticking and alert chimes with instant cancellation."""

import math
import os
import shutil
import struct
import subprocess
import threading
import time
from typing import Optional
import wave

from wake_widget.constants import (
    ASSETS_DIR,
    CHIME_SOUND_PATH,
    DEFAULT_TICK_INTERVAL_SECONDS,
    TICK_SOUND_PATH,
    TOCK_SOUND_PATH,
)


def ensure_sound_assets() -> None:
    """Ensure audio assets exist, generating pleasant synthetic tones if missing."""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    sr = 44100

    def write_wav(path: str, samples: list) -> None:
        if os.path.exists(path):
            return
        with wave.open(path, 'w') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            data = bytearray()
            for s in samples:
                val = max(-32767, min(32767, int(s * 32767)))
                data.extend(struct.pack('<h', val))
            f.writeframes(data)

    # 1. Tick: Crisp mechanical escapement click
    if not os.path.exists(TICK_SOUND_PATH):
        tick_samples = []
        for i in range(int(sr * 0.045)):
            t = i / sr
            env = math.exp(-t * 150)
            s = env * (0.75 * math.sin(2 * math.pi * 1750 * t) + 0.25 * math.sin(2 * math.pi * 875 * t))
            tick_samples.append(s)
        write_wav(TICK_SOUND_PATH, tick_samples)

    # 2. Tock: Companion lower mechanical click
    if not os.path.exists(TOCK_SOUND_PATH):
        tock_samples = []
        for i in range(int(sr * 0.045)):
            t = i / sr
            env = math.exp(-t * 135)
            s = env * (0.75 * math.sin(2 * math.pi * 1250 * t) + 0.25 * math.sin(2 * math.pi * 625 * t))
            tock_samples.append(s)
        write_wav(TOCK_SOUND_PATH, tock_samples)

    # 3. Chime: Dual harmonic bell
    if not os.path.exists(CHIME_SOUND_PATH):
        chime_samples = []
        for i in range(int(sr * 0.65)):
            t = i / sr
            env1 = math.exp(-t * 7.0)
            env2 = math.exp(-max(0.0, t - 0.15) * 6.5) if t >= 0.15 else 0.0
            s = 0.5 * env1 * math.sin(2 * math.pi * 880 * t) + 0.5 * env2 * math.sin(2 * math.pi * 1318.5 * (t - 0.15))
            chime_samples.append(s)
        write_wav(CHIME_SOUND_PATH, chime_samples)


class SoundService:
    """Manages audio playback for ticks, tocks, and alerts."""

    def __init__(self, sound_enabled: bool = True, tick_interval: float = DEFAULT_TICK_INTERVAL_SECONDS) -> None:
        self.sound_enabled = sound_enabled
        self.tick_interval = tick_interval
        ensure_sound_assets()

        self._player_bin = self._find_player()
        self._is_ticking = False
        self._thread: Optional[threading.Thread] = None
        self._current_proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def _find_player(self) -> Optional[str]:
        for candidate in ('paplay', 'pw-play', 'aplay', 'canberra-gtk-play'):
            path = shutil.which(candidate)
            if path:
                return path
        return None

    def play_file(self, path: str, block: bool = False) -> None:
        if not self.sound_enabled or not self._player_bin or not os.path.isfile(path):
            return

        cmd = [self._player_bin, path]
        try:
            with self._lock:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._current_proc = proc

            if block:
                proc.wait(timeout=2.0)
                with self._lock:
                    if self._current_proc == proc:
                        self._current_proc = None
        except Exception:
            pass

    def start_ticking(self) -> None:
        """Start the rhythmic timer ticking loop in a background thread."""
        with self._lock:
            if self._is_ticking:
                return
            self._is_ticking = True
            self._thread = threading.Thread(target=self._ticking_worker, daemon=True)
            self._thread.start()

    def stop_ticking(self) -> None:
        """Immediately stop ticking audio and terminate any running sound process."""
        with self._lock:
            self._is_ticking = False
            if self._current_proc:
                try:
                    self._current_proc.terminate()
                except Exception:
                    pass
                self._current_proc = None

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleeps in 25ms steps; returns False if stopped."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if not self._is_ticking:
                return False
            time.sleep(0.025)
        return True

    def _ticking_worker(self) -> None:
        # Play alert chime once at the start of alert
        if self._is_ticking and os.path.exists(CHIME_SOUND_PATH):
            self.play_file(CHIME_SOUND_PATH, block=False)
            if not self._sleep_interruptible(0.5):
                return

        # Alternating Tick ... Tock loop
        is_tick = True
        interval = max(0.2, self.tick_interval)

        while self._is_ticking:
            sound_path = TICK_SOUND_PATH if is_tick else TOCK_SOUND_PATH
            if os.path.exists(sound_path):
                self.play_file(sound_path, block=False)

            is_tick = not is_tick
            if not self._sleep_interruptible(interval):
                break
