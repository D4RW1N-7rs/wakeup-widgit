"""System-wide user activity monitor for X11 (mouse motion, clicks, and keyboard presses)."""

import ctypes
import ctypes.util
import os
import shutil
import subprocess
import time
from typing import Optional


class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [
        ('window', ctypes.c_ulong),
        ('state', ctypes.c_int),
        ('kind', ctypes.c_int),
        ('til_or_since', ctypes.c_ulong),
        ('idle', ctypes.c_ulong),
        ('event_mask', ctypes.c_ulong),
    ]


class ActivityMonitor:
    """Detects any user activity (mouse movement, mouse clicks, keyboard presses).

    Uses XScreenSaverQueryInfo via ctypes for microsecond-level query speed
    with 0% CPU consumption and no pip or root privileges required.
    """

    def __init__(self) -> None:
        self._display: Optional[int] = None
        self._root: Optional[int] = None
        self._xss_info: Optional[ctypes.POINTER(XScreenSaverInfo)] = None
        self._x11: Optional[ctypes.CDLL] = None
        self._xss: Optional[ctypes.CDLL] = None
        self._fallback_mode: bool = False
        self._last_fallback_check: float = 0.0
        self._last_fallback_idle: float = 0.0

        self._init_x11()

    def _init_x11(self) -> bool:
        if not os.environ.get('DISPLAY'):
            self._fallback_mode = True
            return False

        try:
            x11_path = ctypes.util.find_library('X11') or 'libX11.so.6'
            xss_path = ctypes.util.find_library('Xss') or 'libXss.so.1'

            self._x11 = ctypes.cdll.LoadLibrary(x11_path)
            self._xss = ctypes.cdll.LoadLibrary(xss_path)

            # Declare types for 64-bit safety
            self._x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self._x11.XOpenDisplay.restype = ctypes.c_void_p

            self._x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            self._x11.XDefaultRootWindow.restype = ctypes.c_ulong

            self._x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            self._x11.XCloseDisplay.restype = ctypes.c_int

            self._xss.XScreenSaverAllocInfo.argtypes = []
            self._xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)

            self._xss.XScreenSaverQueryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.POINTER(XScreenSaverInfo),
            ]
            self._xss.XScreenSaverQueryInfo.restype = ctypes.c_int

            self._display = self._x11.XOpenDisplay(None)
            if not self._display:
                self._fallback_mode = True
                return False

            self._root = self._x11.XDefaultRootWindow(self._display)
            self._xss_info = self._xss.XScreenSaverAllocInfo()
            return True
        except Exception:
            self._fallback_mode = True
            return False

    def get_idle_seconds(self) -> float:
        """Returns the number of seconds the system has been idle.

        Any mouse move, mouse button click/release, or key press resets this to 0.
        """
        if not self._fallback_mode and self._display and self._root and self._xss_info:
            try:
                ret = self._xss.XScreenSaverQueryInfo(self._display, self._root, self._xss_info)
                if ret != 0:
                    return float(self._xss_info.contents.idle) / 1000.0
            except Exception:
                pass

        return self._query_fallback_idle()

    def _query_fallback_idle(self) -> float:
        """Fallback to xprintidle if ctypes query is unavailable."""
        now = time.monotonic()
        if now - self._last_fallback_check < 0.2:
            return self._last_fallback_idle

        self._last_fallback_check = now
        xprintidle = shutil.which('xprintidle')
        if xprintidle:
            try:
                res = subprocess.run([xprintidle], capture_output=True, text=True, timeout=1)
                if res.returncode == 0:
                    self._last_fallback_idle = float(res.stdout.strip()) / 1000.0
                    return self._last_fallback_idle
            except Exception:
                pass

        return 0.0

    def close(self) -> None:
        """Closes X11 display connection cleanly."""
        if self._x11 and self._display:
            try:
                self._x11.XCloseDisplay(self._display)
            except Exception:
                pass
            self._display = None
