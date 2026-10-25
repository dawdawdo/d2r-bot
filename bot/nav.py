"""Closed-loop teleport navigation in "world" coordinates relative to the LK waypoint.

World coords = camera offset in screen pixels from the arrival view (x right, y down). Odometry is
phase correlation between consecutive frames: the world scrolls opposite to our movement. Drift
is a few px per hop, fine for distances of a few thousand px.
"""
from __future__ import annotations

import logging
import math

import cv2
import numpy as np

from .controller import BotError, Controller

log = logging.getLogger(__name__)

CENTER = (640, 330)
VIEW_H = 590
MAX_HOP = 300
TP_SETTLE = 0.45


def _small(frame: np.ndarray) -> np.ndarray:
    g = cv2.cvtColor(frame[:VIEW_H], cv2.COLOR_BGR2GRAY)
    return cv2.resize(g, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA).astype(np.float32)


class Odometer:
    def __init__(self, frame: np.ndarray) -> None:
        self.pos = np.array([0.0, 0.0])
        self.prev = _small(frame)
        self.win = cv2.createHanningWindow(self.prev.shape[::-1], cv2.CV_32F)

    def update(self, frame: np.ndarray) -> tuple[float, float]:
        cur = _small(frame)
        (dx, dy), _ = cv2.phaseCorrelate(self.prev, cur, self.win)
        self.prev = cur
        moved = np.array([-dx * 2, -dy * 2])
        self.pos += moved
        return float(moved[0]), float(moved[1])


def hop(bot: Controller, odo: Odometer, dx: float, dy: float) -> tuple[float, float]:
    bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right")
    bot.sleep(TP_SETTLE)
    return odo.update(bot.capture.grab())


def teleport_to(bot: Controller, odo: Odometer, target, tol: float = 70, max_hops: int = 30) -> bool:
    """Teleport until within `tol` px of world `target`. Detours sideways when blocked."""
    target = np.asarray(target, float)
    stuck = 0
    for _ in range(max_hops):
        d = target - odo.pos
        dist = math.hypot(*d)
        if dist <= tol:
            return True
        step = d * min(1.0, MAX_HOP / dist)
        if stuck:  # blocked: try rotated directions (+-60 deg, then +-110 deg)
            ang = [60, -60, 110, -110][(stuck - 1) % 4]
            c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            step = np.array([c * step[0] - s * step[1], s * step[0] + c * step[1]])
        mx, my = hop(bot, odo, *step)
        if math.hypot(mx, my) < 30:
            stuck += 1
            if stuck > 6:
                break
        else:
            stuck = 0
    bot.save_failure("teleport_to_failed")
    log.warning("teleport_to %s failed at %s", target.tolist(), odo.pos.round().tolist())
    return False


def movers(bot: Controller, gap: float = 0.18, min_area: int = 250) -> list[tuple[int, int, int]]:
    """Moving blobs (monsters) between two frames `gap` s apart, excluding the character.
    Returns [(x, y, area)] sorted by area, largest first."""
    a = cv2.cvtColor(bot.capture.grab()[:VIEW_H], cv2.COLOR_BGR2GRAY)
    bot.sleep(gap)
    f = bot.capture.grab()
    b = cv2.cvtColor(f[:VIEW_H], cv2.COLOR_BGR2GRAY)
    d = (cv2.absdiff(a, b) > 25).astype(np.uint8)
    d[CENTER[1] - 70 : CENTER[1] + 40, CENTER[0] - 40 : CENTER[0] + 40] = 0  # our own sprite/effects
    d[:40, 1100:] = 0  # clock
    d = cv2.morphologyEx(d, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(d)
    out = [(int(cen[i][0]), int(cen[i][1]), int(st[i][4])) for i in range(1, n) if st[i][4] >= min_area]
    return sorted(out, key=lambda t: -t[2])


def fight(bot: Controller, max_casts: int = 8) -> int:
    """Cast Frozen Orb at moving monsters until nothing moves (or max_casts). Restores Teleport."""
    sk = bot.cfg["hotkeys"]["skills"]
    casts = 0
    quiet = 0
    bot.press(sk["frozen_orb"])
    try:
        while casts < max_casts and quiet < 2:
            m = movers(bot)
            if not m:
                quiet += 1
                continue
            quiet = 0
            x, y, _ = m[0]
            bot.click(x, y, "right")
            casts += 1
            bot.sleep(0.5)
    finally:
        bot.press(sk["teleport"])
    if casts:
        log.info("fight: %d frozen orbs", casts)
    return casts


def world_to_screen(odo: Odometer, wx: float, wy: float) -> tuple[int, int]:
    return int(CENTER[0] + wx - odo.pos[0]), int(CENTER[1] + wy - odo.pos[1])


def scan_tooltips(bot: Controller, region=(160, 60, 960, 500), step: int = 40) -> list[tuple[int, int, np.ndarray]]:
    """Hover a grid; return points where an object name tooltip appears, with the tooltip crop."""
    rx, ry, rw, rh = region
    hits = []
    for row, y in enumerate(range(ry, ry + rh, step)):
        bot.check()
        bot.input.move(1270, 590)
        bot.sleep(0.12)
        base = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
        for i, x in enumerate(range(rx, rx + rw, step)):
            if i and i % 6 == 0:
                bot.check()  # HP guardian every ~0.5 s
            bot.input.move(x, y)
            bot.kill.sleep(0.08)
            f = bot.capture.grab()
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.int16)
            y0, x0 = max(0, y - 70), max(0, x - 110)
            if (np.abs(g[y0:y, x0 : x + 110] - base[y0:y, x0 : x + 110]) > 60).mean() > 0.03:
                hits.append((x, y, f[y0:y, x0 : x + 110].copy()))
    bot.input.move(1270, 590)
    return hits


__all__ = ["Odometer", "teleport_to", "hop", "world_to_screen", "scan_tooltips", "BotError"]
