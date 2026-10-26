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


MIN_RESPONSE = 0.04  # phase-correlation peak below this = frames barely overlap (tracking lost)
# Phase correlation wraps at half the frame (640 x 295 px), so steps near that are ambiguous.
# Live: 420 px across and 270 px down measured fine (resp > 0.1); 530 px at resp 0.03 did not.
# teleport_to keeps hops within MAX_HOP_Y vertically so normal hops stay clear of the limit.
MAX_STEP_X, MAX_STEP_Y = 520, 280
MAX_HOP_Y = 220


class Odometer:
    """`lost` is set when a step can't be trusted (Blizzaga's teleport-on-hit item jumps her
    randomly mid-fight); re-anchor on a landmark (anchor_bonfire) to clear it."""

    def __init__(self, frame: np.ndarray) -> None:
        self.pos = np.array([0.0, 0.0])
        self.prev = _small(frame)
        self.win = cv2.createHanningWindow(self.prev.shape[::-1], cv2.CV_32F)
        self.lost = False
        self.resp = 1.0
        self.since_anchor = 0.0  # px travelled since the last landmark fix (drift grows with it)

    def update(self, frame: np.ndarray) -> tuple[float, float]:
        cur = _small(frame)
        (dx, dy), self.resp = cv2.phaseCorrelate(self.prev, cur, self.win)
        self.prev = cur
        moved = np.array([-dx * 2, -dy * 2])
        self.pos += moved
        self.since_anchor += math.hypot(*moved)
        if self.resp < MIN_RESPONSE or abs(moved[0]) > MAX_STEP_X or abs(moved[1]) > MAX_STEP_Y:
            if not self.lost:
                log.warning("odometry lost: step %s resp %.3f", moved.round().tolist(), self.resp)
            self.lost = True
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
        step = d * min(1.0, MAX_HOP / dist, MAX_HOP_Y / max(abs(d[1]), 1e-6))
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


def movers(bot: Controller, gap: float = 0.18, min_area: int = 250, odo: Odometer | None = None
           ) -> list[tuple[int, int, int]]:
    """Moving blobs (monsters) between two frames `gap` s apart, excluding the character.
    Returns [(x, y, area)] sorted by area, largest first. Feeds both frames to `odo` if given."""
    f0 = bot.capture.grab()
    if odo is not None:
        odo.update(f0)
    a = cv2.cvtColor(f0[:VIEW_H], cv2.COLOR_BGR2GRAY)
    bot.sleep(gap)
    f = bot.capture.grab()
    if odo is not None:
        odo.update(f)
    b = cv2.cvtColor(f[:VIEW_H], cv2.COLOR_BGR2GRAY)
    d = (cv2.absdiff(a, b) > 25).astype(np.uint8)
    d[CENTER[1] - 70 : CENTER[1] + 40, CENTER[0] - 40 : CENTER[0] + 40] = 0  # our own sprite/effects
    d[:40, 1100:] = 0  # clock
    d = cv2.morphologyEx(d, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(d)
    out = [(int(cen[i][0]), int(cen[i][1]), int(st[i][4])) for i in range(1, n) if st[i][4] >= min_area]
    return sorted(out, key=lambda t: -t[2])


def fight(bot: Controller, max_casts: int = 4, odo: Odometer | None = None) -> int:
    """Cast Frozen Orb at moving monsters until nothing moves (or max_casts). Restores Teleport.
    Pass `odo` to keep odometry running through teleport-on-hit jumps."""
    sk = bot.cfg["hotkeys"]["skills"]
    casts = 0
    quiet = 0
    bot.press(sk["frozen_orb"])
    try:
        while casts < max_casts and quiet < 2:
            m = movers(bot, odo=odo)
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


def find_fires(frame: np.ndarray, min_area: int = 120) -> list[tuple[int, int, int]]:
    """Bright saturated orange/yellow blobs (bonfires, torches): (x, y, area), largest first."""
    hsv = cv2.cvtColor(frame[:VIEW_H], cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (5, 120, 200), (35, 255, 255))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    out = [(int(cen[i][0]), int(cen[i][1]), int(st[i][4])) for i in range(1, n) if st[i][4] >= min_area]
    return sorted(out, key=lambda t: -t[2])


BONFIRE_AREA = 450  # torches are ~100-300 px of flame at 1280x720; bonfires 600-1500


def anchor_bonfire(bot: Controller, odo: Odometer, bonfire_world, max_err: float = 450) -> bool:
    """Snap odometry to a bonfire at known world coords. Picks the bonfire-sized fire nearest to
    where odometry predicts it. Returns False (odometry unchanged) if none is close enough."""
    frame = bot.capture.grab()
    odo.update(frame)
    px, py = world_to_screen(odo, *bonfire_world)
    fires = [f for f in find_fires(frame) if f[2] >= BONFIRE_AREA]
    if not fires:
        log.info("anchor: no bonfire in view (predicted at %d,%d)", px, py)
        return False
    fx, fy, _ = min(fires, key=lambda f: math.hypot(f[0] - px, f[1] - py))
    err = math.hypot(fx - px, fy - py)
    if err > max_err and not odo.lost:
        log.info("anchor: nearest bonfire %d px off prediction; not trusting it", err)
        return False
    odo.pos += np.array([px - fx, py - fy], float)  # seen further right = we are further left
    log.info("anchor: corrected odometry by (%d, %d)%s", px - fx, py - fy, " [was lost]" if odo.lost else "")
    odo.lost = False
    odo.since_anchor = 0.0
    return True


def reanchor(bot: Controller, odo: Odometer, bonfire_world) -> bool:
    """anchor_bonfire; if the bonfire isn't in view, teleport to where odometry thinks it is and
    look again (after a jump the estimate is off, but usually by less than a screen)."""
    if anchor_bonfire(bot, odo, bonfire_world):
        return True
    teleport_to(bot, odo, bonfire_world, tol=150, max_hops=8)
    return anchor_bonfire(bot, odo, bonfire_world)


def world_to_screen(odo: Odometer, wx: float, wy: float) -> tuple[int, int]:
    return int(CENTER[0] + wx - odo.pos[0]), int(CENTER[1] + wy - odo.pos[1])


def scan_tooltips(bot: Controller, region=(160, 60, 960, 500), step: int = 40) -> list[tuple[int, int, np.ndarray]]:
    """Hover a grid; return points where an object name tooltip appears, with the tooltip crop."""
    from .vision.tooltip import find_tooltip

    rx, ry, rw, rh = region
    hits = []
    for y in range(ry, ry + rh, step):
        for i, x in enumerate(range(rx, rx + rw, step)):
            if i % 6 == 0:
                bot.check()  # HP guardian every ~0.5 s
            bot.input.move(x, y)
            bot.kill.sleep(0.08)
            f = bot.capture.grab()
            box = find_tooltip(f, x, y)
            if box is not None:
                bx, by, bw, bh = box
                hits.append((x, y, f[by : by + bh, bx : bx + bw].copy()))
    bot.input.move(1270, 590)
    return hits


__all__ = ["Odometer", "anchor_bonfire", "reanchor", "find_fires", "teleport_to", "hop", "world_to_screen",
           "scan_tooltips", "BotError"]
