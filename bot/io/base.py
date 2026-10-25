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
    def click(self, x: int, y: int, button: str = "left") -> None: ...

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


class HotkeyListener(ABC):
    @abstractmethod
    def start(self, key: str, callback: Callable[[], None]) -> None:
        """Call `callback` (from a background thread) whenever `key` is pressed.
        May be called repeatedly to bind several keys."""

    @abstractmethod
    def stop(self) -> None: ...


class GuardedInput(Input):
    """Wraps an Input so every action first checks the kill switch."""

    def __init__(self, inner: Input, kill) -> None:
        self.inner = inner
        self.kill = kill

    def move(self, x, y):
        self.kill.check()
        self.inner.move(x, y)

    def click(self, x, y, button="left"):
        self.kill.check()
        self.inner.click(x, y, button)

    def key_down(self, key):
        self.kill.check()
        self.inner.key_down(key)

    def key_up(self, key):
        # Releasing is always allowed so nothing stays stuck down.
        self.inner.key_up(key)

    def release_all(self):
        self.inner.release_all()
