"""Cube gems and runes at the stash (Stephen 2026-11-07). The stash panel has its own 3x4 Horadric Cube grid
and Transmute button under every tab. What to cube comes from bot/cube.py; counts from the Gems and Runes tabs.

Moves, all tested live 2026-11-07: Ctrl+Shift+click on a stack slot moves one item into the cube; Transmute
leaves the result in the cube (bottom right); Ctrl+Shift+click on it moves it back onto its stash stack.
"""
from __future__ import annotations

import logging
import time
from collections import Counter

import cv2
import numpy as np

from . import cube, state
from .controller import Controller
from .vision import stack_count as sc
from .config import ROOT

RAW = ROOT / "fixtures" / "raw"

log = logging.getLogger(__name__)

CUBE_CELLS = [(x, y) for y in (324, 362, 400, 439) for x in (186, 224, 263)]
TRANSMUTE = (224, 500)
AWAY = (640, 650)  # mouse parked off the stash: tooltips cover the cube


def cube_items(frame: np.ndarray) -> list[tuple[int, int]]:
    """Cube cells holding something (empty ones are black)."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return [(x, y) for x, y in CUBE_CELLS if float((hsv[y - 14:y + 14, x - 14:x + 14, 2] > 60).mean()) > 0.1]


def slot_of(name: str) -> tuple[str, tuple[int, int]]:
    """(tab, slot center) of a rune or gem by name."""
    if name in cube.RUNES:
        return "runes", sc.slot_center("runes", *sc.RUNE_SLOTS[cube.RUNES.index(name)])
    for r in range(len(sc.GEM_GRADES)):
        for c in range(len(sc.GEM_COLORS)):
            if sc.gem_name(r, c) == name:
                return "gems", sc.slot_center("gems", r, c)
    raise KeyError(name)


class Cuber:
    def __init__(self, bot: Controller):
        self.bot = bot
        self.tab: str | None = None

    def look(self) -> np.ndarray:
        self.bot.input.move(*AWAY)
        self.bot.kill.sleep(0.35)
        return self.bot.capture.grab()

    def open_tab(self, tab: str) -> None:
        if self.tab != tab:
            self.bot.click(*self.bot.cfg["stash"][f"{tab}_tab"])
            self.bot.kill.sleep(0.4)
            self.tab = tab

    def ctrl_shift_click(self, x: int, y: int) -> None:
        bot = self.bot
        bot.input.key_down("ctrl")
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(x, y)
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.input.key_up("ctrl")
        bot.kill.sleep(0.2)

    def counts(self) -> dict[str, int]:
        self.open_tab("runes")
        runes = self.look()
        out = sc.rune_counts(runes)
        self.open_tab("gems")
        gems = self.look()
        out.update(sc.gem_counts(gems))
        try:  # the latest pair, to check misreads against the armory's save-file counts (overwritten each time)
            RAW.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(RAW / "cube_runes_last.png"), runes)
            cv2.imwrite(str(RAW / "cube_gems_last.png"), gems)
        except Exception:
            pass
        return out

    def empty_cube(self) -> bool:
        """Everything in the cube back to the stash. False if something stays (its stack is full)."""
        for _ in range(2):
            items = cube_items(self.look())
            if not items:
                return True
            for x, y in items:
                self.ctrl_shift_click(x, y)
        return not cube_items(self.look())

    def transmute(self, inputs: dict[str, int], out: str) -> bool:
        for name, n in inputs.items():
            tab, pt = slot_of(name)
            self.open_tab(tab)
            for _ in range(n):
                self.ctrl_shift_click(*pt)
        got = len(cube_items(self.look()))
        if got != sum(inputs.values()):
            log.warning("cube: %s -> %s: %d item(s) in the cube, wanted %d", inputs, out, got,
                        sum(inputs.values()))
            self.bot.save_failure("cube_inputs")
            return False
        self.bot.click(*TRANSMUTE)
        self.bot.kill.sleep(0.5)
        if len(cube_items(self.look())) != 1:
            log.warning("cube: %s -> %s: transmute didn't make one item", inputs, out)
            self.bot.save_failure("cube_transmute")
            return False
        return True


def cube_stash(bot: Controller) -> int:
    """With the stash open: plan from the tab counts and transmute. Returns transmutes done."""
    ccfg = bot.cfg.get("cube", {})
    c = Cuber(bot)
    # the cube grid shows under the Gems, Materials and Runes tabs only: on Personal or Shared those cells are the
    # page's own items (2026-11-08 GLaDOS: the stash opened on Personal, "won't go back", no cubing all day)
    c.open_tab("runes")
    if not c.empty_cube():
        log.warning("cube: something in the cube won't go back to the stash; not cubing")
        bot.save_failure("cube_not_empty")
        tries = getattr(bot, "cube_blocked_n", 0) + 1
        bot.cube_blocked_n = tries
        bot.cube_blocked = tries < 3  # 3 town visits in a row: something really is stuck; back to the 6 h timer
        return 0
    bot.cube_blocked, bot.cube_blocked_n = False, 0
    before = c.counts()
    steps = cube.plan(before, keep=ccfg.get("keep", cube.KEEP), top=ccfg.get("top_rune", cube.TOP_RUNE),
                      top_grade=ccfg.get("top_grade", cube.TOP_GRADE), gem_keep=ccfg.get("gem_keep", cube.GEM_KEEP))
    steps = steps[:ccfg.get("max_transmutes", 200)]
    log.info("cube: %d transmute(s) planned: %s", len(steps), dict(Counter(o for _, o in steps)))
    log.info("cube: counts read: %s", {k: v for k, v in before.items() if v})
    if short := cube.gem_short(before, steps, keep=ccfg.get("keep", cube.KEEP), top=ccfg.get("top_rune", cube.TOP_RUNE),
                                gem_keep=ccfg.get("gem_keep", cube.GEM_KEEP)):
        log.info("cube: runes waiting on their gem (runes, gem, gems): %s", short)
    t0 = time.monotonic()
    done = 0
    for inputs, out in steps:
        ok = c.transmute(inputs, out)
        if not c.empty_cube():
            log.warning("cube: %s won't go back to the stash (stack full?); stopping", out)
            bot.save_failure("cube_stuck")
            break
        if not ok:
            break
        done += 1
    after = c.counts()
    want = Counter(before)
    for inputs, out in steps[:done]:
        want.subtract(inputs)
        want[out] += 1
    off = {k: (after.get(k, 0), want[k]) for k in want if after.get(k, 0) != want[k]}
    log.info("cube: %d transmute(s) in %.0fs; counts that differ from the plan (read, expected): %s",
             done, time.monotonic() - t0, off or "none")
    return done


def cube_if_due(bot: Controller) -> int:
    """Every `cube.every_hours`: open the stash and cube. In town only."""
    from .town import open_stash

    ccfg = bot.cfg.get("cube", {})
    if not ccfg.get("enabled", False):
        return 0
    st = state.load()
    if time.time() - st.get("cubed_at", 0) < ccfg.get("every_hours", 6) * 3600:
        return 0
    if not open_stash(bot):
        return 0
    try:
        done = cube_stash(bot)
    finally:
        bot.press("esc")
        bot.kill.sleep(0.5)
    if getattr(bot, "cube_blocked", False):
        return done  # not cubed: try again at the next town visit, not in 6 h
    st = state.load()
    st["cubed_at"] = time.time()
    state.save(st)
    return done
