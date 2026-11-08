"""Capture and hotkey classes shared by the Windows and Linux (X11) backends."""
from __future__ import annotations

import logging
from typing import Callable

import cv2
import mss
import numpy as np
from pynput import keyboard, mouse

from .base import Capture, ClickListener, HotkeyListener, Region, Window

log = logging.getLogger(__name__)

_MSS = getattr(mss, "MSS", None) or mss.mss  # mss >= 10.2 renamed the factory


def grab_clamped(sct, left: int, top: int, width: int, height: int) -> np.ndarray:
    """Grab a screen rectangle as BGR. Any part outside the desktop comes back black:
    X11 refuses (BadMatch) a grab that crosses the screen edge, Windows just pads."""
    desk = sct.monitors[0]
    out = np.zeros((height, width, 3), np.uint8)
    x0, y0 = max(left, desk["left"]), max(top, desk["top"])
    x1 = min(left + width, desk["left"] + desk["width"])
    y1 = min(top + height, desk["top"] + desk["height"])
    if x1 <= x0 or y1 <= y0:
        return out
    shot = _bgr(sct.grab({"left": x0, "top": y0, "width": x1 - x0, "height": y1 - y0}))
    if shot.shape[:2] == out.shape[:2]:
        return shot
    out[y0 - top:y1 - top, x0 - left:x1 - left] = shot
    return out


def _bgr(shot) -> np.ndarray:
    """mss ScreenShot -> BGR array. np.asarray(shot) goes through a slow per-pixel path (18 ms for 1280x720
    on GLaDOS); viewing the raw BGRA bytes and dropping alpha with OpenCV takes ~2 ms."""
    w, h = shot.size
    return cv2.cvtColor(np.frombuffer(shot.bgra, np.uint8).reshape(h, w, 4), cv2.COLOR_BGRA2BGR)


class DesktopCapture(Capture):
    """Whole primary monitor (for diagnostics when the game window isn't found)."""

    def __init__(self) -> None:
        self.sct = _MSS()

    def grab(self, region: Region | None = None) -> np.ndarray:
        mon = self.sct.monitors[1]
        if region is not None:
            x, y, w, h = region
            return grab_clamped(self.sct, mon["left"] + x, mon["top"] + y, w, h)
        return _bgr(self.sct.grab(mon))

    def close(self) -> None:
        self.sct.close()


def gamma_lut(gamma: float, toe: tuple[int, int] = (4, 16)) -> np.ndarray | None:
    """256-entry LUT for out = 255 * (in/255) ** gamma, or None for gamma 1 (no-op).

    `toe` keeps near-black black: inputs up to toe[0] pass unchanged, then a straight line joins the
    curve at toe[1]. A pure power curve lifts 1 -> 5, 2 -> 9, 3 -> 11, and the tooltip finder looks for
    boxes darker than 8 (Windows draws them at 0-3): LK chest tooltips got clipped (2026-11-08)."""
    if abs(gamma - 1.0) < 1e-6:
        return None
    v = np.arange(256, dtype=np.float64)
    out = 255.0 * (v / 255.0) ** gamma
    lo, hi = toe
    if hi > lo:
        out[: lo + 1] = v[: lo + 1]
        out[lo:hi + 1] = np.interp(v[lo:hi + 1], [lo, hi], [lo, out[hi]])
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


class MssCapture(Capture):
    """Grabs the game's client area. `gamma` < 1 brightens frames to match the Windows
    reference: under Proton, D2R's in-game Gamma setting has no effect (measured 0.70 on GLaDOS)."""

    def __init__(self, window: Window, gamma: float = 1.0) -> None:
        self.window = window
        self.sct = _MSS()
        self.lut = gamma_lut(gamma)

    def grab(self, region: Region | None = None) -> np.ndarray:
        wx, wy, ww, wh = self.window.client_rect()
        if region is None:
            region = (0, 0, ww, wh)
        x, y, w, h = region
        frame = grab_clamped(self.sct, wx + x, wy + y, w, h)
        return frame if self.lut is None else cv2.LUT(frame, self.lut)  # numpy lut[frame] took 13 ms

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


class PynputClicks(ClickListener):
    def __init__(self) -> None:
        self.listener: mouse.Listener | None = None

    def start(self, callback: Callable[[int, int, str], None],
              on_release: Callable[[int, int, str], None] | None = None) -> None:
        def on_click(x, y, button, pressed) -> None:
            if button in (mouse.Button.left, mouse.Button.right):
                cb = callback if pressed else on_release
                if cb is None:
                    return
                try:
                    cb(int(x), int(y), button.name)
                except Exception:
                    log.exception("click callback failed")

        self.listener = mouse.Listener(on_click=on_click, daemon=True)
        self.listener.start()

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
