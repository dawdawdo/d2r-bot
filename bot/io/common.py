"""Capture and hotkey classes shared by the Windows and Linux (X11) backends."""
from __future__ import annotations

import logging
from typing import Callable

import mss
import numpy as np
from pynput import keyboard

from .base import Capture, HotkeyListener, Region, Window

log = logging.getLogger(__name__)

_MSS = getattr(mss, "MSS", None) or mss.mss  # mss >= 10.2 renamed the factory


def grab_clamped(sct, left: int, top: int, width: int, height: int) -> np.ndarray:
    """Grab a screen rectangle as BGR. Any part outside the desktop comes back black:
    X11 refuses (BadMatch) a grab that crosses the screen edge, Windows just pads."""
    out = np.zeros((height, width, 3), np.uint8)
    desk = sct.monitors[0]
    x0, y0 = max(left, desk["left"]), max(top, desk["top"])
    x1 = min(left + width, desk["left"] + desk["width"])
    y1 = min(top + height, desk["top"] + desk["height"])
    if x1 <= x0 or y1 <= y0:
        return out
    shot = np.asarray(sct.grab({"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}))[:, :, :3]
    out[y0 - top:y1 - top, x0 - left:x1 - left] = shot
    return out


class DesktopCapture(Capture):
    """Whole primary monitor (for diagnostics when the game window isn't found)."""

    def __init__(self) -> None:
        self.sct = _MSS()

    def grab(self, region: Region | None = None) -> np.ndarray:
        mon = self.sct.monitors[1]
        if region is not None:
            x, y, w, h = region
            return grab_clamped(self.sct, mon["left"] + x, mon["top"] + y, w, h)
        return np.ascontiguousarray(np.asarray(self.sct.grab(mon))[:, :, :3])

    def close(self) -> None:
        self.sct.close()


class MssCapture(Capture):
    def __init__(self, window: Window) -> None:
        self.window = window
        self.sct = _MSS()

    def grab(self, region: Region | None = None) -> np.ndarray:
        wx, wy, ww, wh = self.window.client_rect()
        if region is None:
            region = (0, 0, ww, wh)
        x, y, w, h = region
        return grab_clamped(self.sct, wx + x, wy + y, w, h)

    def close(self) -> None:
        self.sct.close()


class PynputHotkeys(HotkeyListener):
    """One background listener; `start` may be called once per key to add bindings."""

    def __init__(self) -> None:
        self.listener: keyboard.Listener | None = None
        self.bindings: dict = {}

    def start(self, key: str, callback: Callable[[], None]) -> None:
        target = getattr(keyboard.Key, key.lower(), None) or keyboard.KeyCode.from_char(key)
        self.bindings[target] = callback
        if self.listener is None:
            self.listener = keyboard.Listener(on_press=self._on_press, daemon=True)
            self.listener.start()

    def _on_press(self, k) -> None:
        cb = self.bindings.get(k)
        if cb is not None:
            try:
                cb()
            except Exception:
                log.exception("hotkey callback failed")

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.bindings.clear()
