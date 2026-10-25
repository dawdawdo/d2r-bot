"""Windows backend: user32 window lookup, mss capture, pydirectinput input, pynput hotkeys."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import logging
from typing import Callable

import mss
import numpy as np
import pydirectinput
from pynput import keyboard

from .base import Capture, HotkeyListener, Input, Region, Window

log = logging.getLogger(__name__)

pydirectinput.FAILSAFE = False  # we have our own kill switch
pydirectinput.PAUSE = 0.02

_user32 = ctypes.windll.user32
try:  # make GetClientRect/ClientToScreen return physical pixels
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


class Win32Window(Window):
    def __init__(self, title: str) -> None:
        self.title = title
        self.hwnd = _user32.FindWindowW(None, title)
        if not self.hwnd:
            raise RuntimeError(f"window not found: {title!r}")

    def client_rect(self) -> Region:
        rc = wt.RECT()
        _user32.GetClientRect(self.hwnd, ctypes.byref(rc))
        pt = wt.POINT(0, 0)
        _user32.ClientToScreen(self.hwnd, ctypes.byref(pt))
        return pt.x, pt.y, rc.right - rc.left, rc.bottom - rc.top

    def is_foreground(self) -> bool:
        return _user32.GetForegroundWindow() == self.hwnd

    def focus(self) -> None:
        _user32.SetForegroundWindow(self.hwnd)


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


_BUTTONS = {"left": pydirectinput.LEFT, "right": pydirectinput.RIGHT, "middle": pydirectinput.MIDDLE}


class DirectInput(Input):
    def __init__(self, window: Window) -> None:
        self.window = window
        self.held: set[str] = set()

    def _abs(self, x: int, y: int) -> tuple[int, int]:
        wx, wy, _, _ = self.window.client_rect()
        return wx + x, wy + y

    def move(self, x, y):
        pydirectinput.moveTo(*self._abs(x, y))

    def click(self, x, y, button="left"):
        ax, ay = self._abs(x, y)
        pydirectinput.click(ax, ay, button=_BUTTONS[button])

    def key_down(self, key):
        self.held.add(key)
        pydirectinput.keyDown(key)

    def key_up(self, key):
        self.held.discard(key)
        pydirectinput.keyUp(key)

    def release_all(self):
        for k in list(self.held):
            self.key_up(k)
        for b in _BUTTONS.values():
            pydirectinput.mouseUp(button=b)


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
