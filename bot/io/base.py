"""Platform-neutral interfaces for capture, input, hotkeys and the game window.

All coordinates passed to these interfaces are *client-relative* (0,0 = top-left of
the game's client area), so callers never care where the window sits on screen.
Frames are numpy uint8 BGR arrays of shape (h, w, 3).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

import numpy as np

Region = tuple[int, int, int, int]  # x, y, w, h (client-relative)


class Window(ABC):
    @abstractmethod
    def client_rect(self) -> Region:
        """Client area in *screen* coordinates (x, y, w, h)."""

    @abstractmethod
    def is_foreground(self) -> bool: ...

    @abstractmethod
    def focus(self) -> None: ...


class Capture(ABC):
    @abstractmethod
    def grab(self, region: Region | None = None) -> np.ndarray:
        """Grab the client area (or a client-relative sub-region) as BGR."""

    def close(self) -> None:
        pass


class Input(ABC):
    @abstractmethod
    def move(self, x: int, y: int) -> None: ...

    @abstractmethod
    def click(self, x: int, y: int, button: str = "left", hover: float = 0.08) -> None:
        """`hover` = seconds the cursor rests before the press (objects need it; teleport doesn't)."""

    @abstractmethod
    def key_down(self, key: str) -> None: ...

    @abstractmethod
    def key_up(self, key: str) -> None: ...

    def press(self, key: str) -> None:
        self.key_down(key)
        self.key_up(key)

    @abstractmethod
    def release_all(self) -> None:
        """Release any held keys/buttons (called on kill/exit)."""

    def cursor_pos(self) -> tuple[int, int] | None:
        """Current cursor position (client coords), or None if unknown."""
        return None


class HotkeyListener(ABC):
    @abstractmethod
    def start(self, key: str, callback: Callable[[], None]) -> None:
        """Call `callback` (from a background thread) whenever `key` is pressed.
        May be called repeatedly to bind several keys."""

    @abstractmethod
    def stop(self) -> None: ...


class GuardedInput(Input):
    """Wraps an Input so every action first checks the kill switch.

    It also trips the kill switch if the cursor is no longer where we last put it,
    i.e. a human has grabbed the mouse.
    """

    # D2R shifts the camera (and warps the cursor with it) by exactly this many pixels
    # horizontally when a side panel (waypoint, inventory, ...) opens or closes.
    GAME_WARPS_DX = (240, -240)

    def __init__(self, inner: Input, kill, user_move_tol: int = 25) -> None:
        self.inner = inner
        self.kill = kill
        self.tol = user_move_tol
        self.expected: tuple[int, int] | None = None

    def _check(self) -> None:
        self.kill.check()
        pos = self.inner.cursor_pos()
        if self.expected is not None and pos is not None:
            dx, dy = pos[0] - self.expected[0], pos[1] - self.expected[1]
            if dx * dx + dy * dy <= self.tol * self.tol:
                return
            if abs(dy) <= 2 and any(abs(dx - w) <= 2 for w in self.GAME_WARPS_DX):
                return  # panel camera shift, not a human
            self.kill.trip(f"mouse moved by user (expected {self.expected}, at {pos})")
            self.kill.check()

    def move(self, x, y):
        self._check()
        self.inner.move(x, y)
        self.expected = (x, y)

    def click(self, x, y, button="left", hover=0.08):
        self._check()
        self.inner.click(x, y, button, hover)
        self.expected = (x, y)

    def key_down(self, key):
        self._check()
        self.inner.key_down(key)

    def cursor_pos(self):
        return self.inner.cursor_pos()

    def key_up(self, key):
        # Releasing is always allowed so nothing stays stuck down.
        self.inner.key_up(key)

    def release_all(self):
        self.inner.release_all()
