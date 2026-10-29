"""In-memory backends for offline tests: frames from files, input recorded to a list."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np

from .base import ClickListener, Capture, HotkeyListener, Input, Region, Window


class FakeWindow(Window):
    def __init__(self, w: int = 1280, h: int = 720, x: int = 0, y: int = 0) -> None:
        self.rect = (x, y, w, h)

    def client_rect(self) -> Region:
        return self.rect

    def is_foreground(self) -> bool:
        return True

    def focus(self) -> None:
        pass


class FakeCapture(Capture):
    """Serves frames from arrays or image paths, cycling through them."""

    def __init__(self, frames: Iterable[np.ndarray | str | Path]) -> None:
        self.frames = [f if isinstance(f, np.ndarray) else cv2.imread(str(f)) for f in frames]
        if not self.frames or any(f is None for f in self.frames):
            raise ValueError("FakeCapture needs readable frames")
        self.i = 0

    def grab(self, region: Region | None = None) -> np.ndarray:
        frame = self.frames[self.i % len(self.frames)]
        self.i += 1
        if region is not None:
            x, y, w, h = region
            frame = frame[y : y + h, x : x + w]
        return frame.copy()


class FakeInput(Input):
    def __init__(self) -> None:
        self.events: list[tuple] = []
        self.held: set[str] = set()
        self.pos = (0, 0)

    def move(self, x, y):
        self.pos = (x, y)
        self.events.append(("move", x, y))

    def click(self, x, y, button="left", hover=0.08):
        self.pos = (x, y)
        self.events.append(("click", x, y, button))

    def cursor_pos(self):
        return self.pos

    def key_down(self, key):
        self.held.add(key)
        self.events.append(("down", key))

    def key_up(self, key):
        self.held.discard(key)
        self.events.append(("up", key))

    def release_all(self):
        for k in list(self.held):
            self.key_up(k)


class FakeHotkeys(HotkeyListener):
    def __init__(self) -> None:
        self.bindings: dict[str, Callable[[], None]] = {}

    def start(self, key, callback):
        self.bindings[key] = callback

    def stop(self):
        self.bindings.clear()

    def fire(self, key: str) -> None:
        self.bindings[key]()


class FakeClicks(ClickListener):
    def __init__(self) -> None:
        self.callback = None

    def start(self, callback):
        self.callback = callback

    def stop(self):
        self.callback = None

    def press(self, x: int, y: int, button: str = "right") -> None:
        if self.callback:
            self.callback(x, y, button)
