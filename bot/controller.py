"""Bot controller: ties capture, classifier and guarded input together.

Every observe/act call checks the kill switch. Input is only sent while the game
window is in the foreground, so a stray click never lands in another app.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from .io import Capture, GuardedInput, Input, Window
from .killswitch import KillSwitch

log = logging.getLogger(__name__)


class BotError(RuntimeError):
    """A step failed (timeout, unexpected screen). The run should be aborted/recovered."""


class Controller:
    def __init__(self, window: Window, capture: Capture, inp: Input, classifier, kill: KillSwitch,
                 cfg: dict, clock=time.monotonic) -> None:
        self.window = window
        self.capture = capture
        self.input = GuardedInput(inp, kill)
        self.classifier = classifier
        self.kill = kill
        self.cfg = cfg
        self.clock = clock
        self.frame: np.ndarray | None = None
        self.state = "unknown"
        self.poll = 0.25  # seconds between observations in wait_for

    # --- perception -------------------------------------------------------
    def observe(self) -> str:
        self.kill.check()
        self.frame = self.capture.grab()
        self.state = self.classifier.classify(self.frame)
        return self.state

    def wait_for(self, states: str | Iterable[str], timeout: float, poll: float | None = None) -> str:
        want = {states} if isinstance(states, str) else set(states)
        poll = self.poll if poll is None else poll
        deadline = self.clock() + timeout
        while True:
            s = self.observe()
            if s in want:
                return s
            if self.clock() >= deadline:
                self.save_failure(f"wait_for_{'_'.join(sorted(want))}_got_{s}")
                raise BotError(f"timeout waiting for {sorted(want)}; last state {s!r}")
            self.kill.sleep(poll)

    # --- action -----------------------------------------------------------
    def _ensure_foreground(self, timeout: float = 5.0) -> None:
        deadline = self.clock() + timeout
        while not self.window.is_foreground():
            if self.clock() >= deadline:
                raise BotError("game window is not in the foreground; refusing to send input")
            self.kill.sleep(0.25)

    def click(self, x: int, y: int, button: str = "left") -> None:
        self._ensure_foreground()
        self.input.click(x, y, button)

    def click_ui(self, name: str) -> None:
        """Click a named point from config `ui` (client coords)."""
        x, y = self.cfg["ui"][name]
        log.debug("click %s at (%d, %d)", name, x, y)
        self.click(x, y)

    def press(self, key: str) -> None:
        self._ensure_foreground()
        self.input.press(key)

    def release_all(self) -> None:
        self.input.release_all()

    # --- diagnostics ------------------------------------------------------
    def save_failure(self, note: str) -> Path | None:
        if self.frame is None:
            return None
        d = Path(self.cfg["paths"]["failures"])
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{time.strftime('%Y%m%d-%H%M%S')}_{note}.png"
        cv2.imwrite(str(p), self.frame)
        log.warning("saved failure frame %s", p.name)
        return p
