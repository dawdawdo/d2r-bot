"""Capture and hotkey classes shared by the Windows and Linux (X11) backends."""
from __future__ import annotations

import logging
from typing import Callable

import mss
import numpy as np
from pynput import keyboard

from .base import Capture, HotkeyListener, Region, Window

log = logging.getLogger(__name__)


class DesktopCapture(Capture):
    """Whole primary monitor (for diagnostics when the game window isn't found)."""

    def __init__(self) -> None:
        self.sct = mss.mss()

    def grab(self, region: Region | None = None) -> np.ndarray:
        mon = self.sct.monitors[1]
        if region is not None:
            x, y, w, h = region
            mon = {"left": mon["left"] + x, "top": mon["top"] + y, "width": w, "height": h}
        return np.ascontiguousarray(np.asarray(self.sct.grab(mon))[:, :, :3])

    def close(self) -> None:
        self.sct.close()


class MssCapture(Capture):
    def __init__(self, window: Window) -> None:
        self.window = window
        self.sct = mss.mss()

    def grab(self, region: Region | None = None) -> np.ndarray:
        wx, wy, ww, wh = self.window.client_rect()
        if region is None:
            region = (0, 0, ww, wh)
        x, y, w, h = region
        shot = self.sct.grab({"left": wx + x, "top": wy + y, "width": w, "height": h})
        return np.ascontiguousarray(np.asarray(shot)[:, :, :3])  # BGRA -> BGR

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
