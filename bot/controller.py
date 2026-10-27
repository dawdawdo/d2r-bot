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


class Chicken(BotError):
    """HP fell below the chicken threshold: leave the game now."""


class Died(BotError):
    """HP orb is empty: the character is dead."""


class RunTimeout(BotError):
    """The run went past its deadline while out of town (stuck somewhere)."""


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
        self.deadline: float | None = None  # clock() time; checked while guarding (out of town)
        self.state = "unknown"
        self.poll = 0.25  # seconds between observations in wait_for
        self._templates: dict[str, np.ndarray] = {}
        # HP guardian: active only while out of town (enable with guard(True)).
        self.guarding = False
        self.hp: float | None = None
        self.mp: float | None = None
        self._last_potion = -99.0

    # --- perception -------------------------------------------------------
    def observe(self) -> str:
        self.kill.check()
        self.frame = self.capture.grab()
        self.state = self.classifier.classify(self.frame)
        if self.state == "in_game":
            self._check_vitals()
        self._check_deadline()
        return self.state

    def guard(self, on: bool) -> None:
        self.guarding = on

    def _check_vitals(self) -> None:
        from .vision.orbs import orb_pcts

        orbs = orb_pcts(self.frame, self.cfg["vision"]["orbs"])
        self.hp, self.mp = orbs["hp"], orbs["mp"]
        if not self.guarding:
            return
        s = self.cfg["safety"]
        if self.hp <= 1:
            self.save_failure("died")
            raise Died("HP orb empty")
        if self.hp < s["chicken_hp_pct"]:
            self.save_failure(f"chicken_hp{int(self.hp)}")
            raise Chicken(f"HP {self.hp}% < {s['chicken_hp_pct']}%")
        # Energy Shield gone (mana empty) while already hurt: life falls very fast from here.
        if self.mp < s.get("es_broken_mp_pct", 0) and self.hp < s.get("es_broken_hp_pct", 0):
            # A belt rejuv refills mana and the shield is back: drink once; still broken after the
            # cooldown (or nothing to drink) -> chicken. (2026-10-27: most chickens were this, HP ~70%.)
            key = self.potion_key() if self.clock() - self._last_potion > s.get("potion_cooldown_s", 1.5) else None
            if key is not None:
                self._last_potion = self.clock()
                log.info("energy shield broken (HP %.0f%% MP %.0f%%) -> potion %s", self.hp, self.mp, key)
                self._ensure_foreground()
                self.input.press(key)
                return
            self.save_failure(f"chicken_es_hp{int(self.hp)}_mp{int(self.mp)}")
            raise Chicken(f"energy shield broken: MP {self.mp}%, HP {self.hp}%")
        low = self.hp < s["potion_hp_pct"] or self.mp < s.get("potion_mp_pct", 0)
        if low and self.clock() - self._last_potion > self.cfg["safety"].get("potion_cooldown_s", 1.5):
            self._last_potion = self.clock()
            key = self.potion_key()
            if key is None:
                log.warning("HP %.0f%%: belt is empty", self.hp)
                return
            log.info("HP %.0f%% MP %.0f%% -> potion %s", self.hp, self.mp, key)
            self._ensure_foreground()
            self.input.press(key)

    def potion_key(self) -> str | None:
        """Hotkey of the first belt slot that still holds a potion (None if all empty)."""
        from .vision.orbs import belt_slots

        frame = self.frame if self.frame is not None else self.capture.grab()
        for key, full in zip(self.cfg["hotkeys"]["potions"], belt_slots(frame, self.cfg["vision"]["belt"])):
            if full:
                return key
        return None

    def check(self) -> None:
        """Cheap guardian tick for tight loops: observe (which runs the HP checks)."""
        self.observe()

    def sleep(self, seconds: float, tick: float = 0.1) -> None:
        """Kill-switch-aware sleep that keeps checking HP while guarding."""
        end = self.clock() + seconds
        while True:
            left = end - self.clock()
            if left <= 0:
                return
            self.kill.sleep(min(tick, left))
            if self.guarding:
                self._guard_frame(self.capture.grab())

    def _guard_frame(self, frame: np.ndarray) -> None:
        """Run the HP checks on a frame, but only if it really is gameplay (not loading/menus)."""
        if not self.guarding:
            return
        self.frame = frame
        self.state = self.classifier.classify(frame)
        if self.state == "in_game":
            self._check_vitals()
        self._check_deadline()

    def _check_deadline(self) -> None:
        if self.guarding and self.deadline is not None and self.clock() > self.deadline:
            self.deadline = None  # raise once; save & exit must be able to run
            raise RunTimeout("run timeout: still out of town past the deadline")

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

    def wait_still(self, timeout: float = 6.0, thresh: float = 2.5, settle: int = 2,
                   poll: float = 0.15, min_wait: float = 0.3) -> bool:
        """Wait until the view stops moving (character finished walking). Returns False on timeout."""
        self.sleep(min_wait)
        deadline = self.clock() + timeout
        prev = None
        calm = 0
        while self.clock() < deadline:
            full = self.capture.grab()
            self._guard_frame(full)
            f = cv2.resize(full[:590], (160, 74), interpolation=cv2.INTER_AREA)
            if prev is not None:
                calm = calm + 1 if np.abs(f.astype(np.int16) - prev).mean() < thresh else 0
                if calm >= settle:
                    return True
            prev = f.astype(np.int16)
            self.kill.sleep(poll)
        return False

    def find(self, template: str, region=None, threshold: float = 0.8) -> tuple[int, int] | None:
        """Top-left of the best match of bot/assets/templates/<template> in the current frame."""
        from .vision.screen import ASSETS, match_score

        img = self._templates.get(template)
        if img is None:
            img = cv2.imread(str(ASSETS / template))
            if img is None:
                raise FileNotFoundError(template)
            self._templates[template] = img
        self.observe()
        score, loc = match_score(self.frame, img, region)
        log.debug("find %s score %.2f at %s", template, score, loc)
        return loc if score >= threshold else None

    # --- action -----------------------------------------------------------
    def _ensure_foreground(self, timeout: float = 5.0) -> None:
        """Popups (notifications, a desktop menu) steal focus: take it back, or give up after `timeout`."""
        deadline = self.clock() + timeout
        while not self.window.is_foreground():
            if self.clock() >= deadline:
                raise BotError("game window is not in the foreground; refusing to send input")
            log.info("game window lost focus; refocusing")
            self.window.focus()
            self.kill.sleep(0.25)

    def click(self, x: int, y: int, button: str = "left", hover: float = 0.08) -> None:
        _, _, w, h = self.window.client_rect()
        if not (0 <= x < w and 0 <= y < h):  # outside the client = clicking the desktop (2026-10-26:
            log.warning("click (%d, %d) outside the game window; clamped", x, y)  # opened its menu)
            x, y = min(max(int(x), 2), w - 3), min(max(int(y), 2), h - 3)
        if self.guarding:
            self.observe()
        self._ensure_foreground()
        self.input.click(x, y, button, hover)

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
