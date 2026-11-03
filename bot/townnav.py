"""Walk a town by its view map (bot.vision.viewmap): find where we are from what's on screen, click toward a
target (the waypoint), and optionally learn new views on the way (tools/town_map.py explores with learn=True).

Positions are world px (see viewmap). Between map fixes we dead-reckon by chaining frame-to-frame offsets
captured every ~0.3 s while walking (consecutive frames overlap a lot, so the chain is reliable).
"""
from __future__ import annotations

import logging
import math

import numpy as np

from .controller import BotError, Controller
from .vision.viewmap import MIN_VOTES, ViewMap, features, offset

log = logging.getLogger(__name__)

CENTER = (640, 330)       # the player's feet on screen (view centre is (640, 360); clicks are relative to her)
STEP = 330                # px: one click's reach (clicks stay inside the walk box)
BOX = (60, 1220, 70, 560)  # x0, x1, y0, y1: clickable ground (not the HUD, the edges, or the merc portrait)
KEYFRAME_GAP = 220        # learn a new view this far from every known one
POLL = 0.3


class Walker:
    def __init__(self, bot: Controller, vmap: ViewMap, learn: bool = False):
        self.bot, self.vmap, self.learn = bot, vmap, learn
        self.pos: tuple[float, float] | None = None   # world position (None = not anchored to the map yet)
        self.chain: list = []                          # (frame, rel pos) seen before anchoring (learn mode)
        self.rel = (0.0, 0.0)
        self.feats = None
        self.blocked: dict[tuple[int, int, int], int] = {}  # (cell x, cell y, direction) -> stalls

    # --- position --------------------------------------------------------------------------------
    def fix(self) -> bool:
        """Locate the current view on the map. True if anchored."""
        frame = self.bot.capture.grab()
        f = features(frame)
        hit = self.vmap.locate(frame, f, near=self.pos, radius=900) if self.pos else None
        if hit is None:
            hit = self.vmap.locate(frame, f)
        self.feats, self._frame = f, frame
        if hit is None:
            return self.pos is not None
        if self.pos is None and self.learn and self.chain:
            # the walk so far (relative to the spawn) joins the map: shift it into world coordinates
            sx, sy = hit[0][0] - self.rel[0], hit[0][1] - self.rel[1]
            for fr, (rx, ry) in self.chain:
                if self.vmap.nearest((rx + sx, ry + sy)) > KEYFRAME_GAP:
                    self.vmap.add(fr, (rx + sx, ry + sy))
            log.info("joined the map: %d views from this spawn", len(self.chain))
            self.chain = []
        self.pos = hit[0]
        return True

    def _track(self, timeout: float = 5.0) -> float:
        """While walking: chain offsets until the view stops moving. Returns distance moved (px)."""
        moved, still, t0 = 0.0, 0, self.bot.clock()
        while self.bot.clock() - t0 < timeout:
            self.bot.kill.sleep(POLL)
            self.bot.check()
            frame = self.bot.capture.grab()
            f = features(frame)
            (dx, dy), n = offset(self.feats, f) if self.feats is not None else ((0.0, 0.0), 0)
            if n < MIN_VOTES:  # lost the thread (a loading flash, a panel): re-fix from the map
                self.feats, self._frame = f, frame
                hit = self.vmap.locate(frame, f)
                if hit:
                    self.pos = hit[0]
                continue
            self.feats, self._frame = f, frame
            moved += math.hypot(dx, dy)
            if self.pos is not None:
                self.pos = (self.pos[0] + dx, self.pos[1] + dy)
            self.rel = (self.rel[0] + dx, self.rel[1] + dy)
            if self.learn:
                self._remember(frame)
            still = still + 1 if math.hypot(dx, dy) < 4 else 0
            if still >= 2:
                break
        return moved

    def _remember(self, frame) -> None:
        if self.pos is not None:
            if self.vmap.nearest(self.pos) > KEYFRAME_GAP:
                self.vmap.add(frame, self.pos)
        elif not self.chain or math.hypot(self.rel[0] - self.chain[-1][1][0], self.rel[1] - self.chain[-1][1][1]) > KEYFRAME_GAP:
            self.chain.append((frame, self.rel))

    # --- moving ----------------------------------------------------------------------------------
    def step(self, dx: float, dy: float) -> float:
        """Click (dx, dy) px from the player (scaled into the walk box); returns px moved."""
        n = math.hypot(dx, dy) or 1.0
        s = min(1.0, STEP / n)
        x = int(np.clip(CENTER[0] + dx * s, BOX[0], BOX[1]))
        y = int(np.clip(CENTER[1] + dy * s, BOX[2], BOX[3]))
        self.bot.click(x, y)
        moved = self._track()
        if moved < 30:
            self._unstick()
        return moved

    def _unstick(self) -> None:
        """No movement: maybe an NPC's dialog opened (clicked on him). Esc closes it; Esc again if that opened
        the game menu instead."""
        self.bot.press("esc")
        self.bot.kill.sleep(0.4)
        if self.bot.observe() == "esc_menu":
            self.bot.press("esc")
            self.bot.kill.sleep(0.4)

    def _dirs(self, n: int = 12):
        return [(math.cos(2 * math.pi * i / n) * STEP * 1.5, math.sin(2 * math.pi * i / n) * STEP * 0.8)
                for i in range(n)]

    def _cell(self, i: int) -> tuple[int, int, int]:
        p = self.pos if self.pos is not None else self.rel
        return (int(p[0] // 250), int(p[1] // 250), i)

    def explore_step(self) -> None:
        """Walk toward the least-known direction (learn mode), avoiding directions that stalled here."""
        p = self.pos if self.pos is not None else self.rel
        best, bi = -1.0, 0
        for i, (dx, dy) in enumerate(self._dirs()):
            q = (p[0] + dx, p[1] + dy)
            if self.pos is not None:
                score = min(self.vmap.nearest(q), 1500)
            else:  # not on the map yet: away from where this spawn's walk has been
                score = min([math.hypot(q[0] - r[0], q[1] - r[1]) for _, r in self.chain] or [1500])
            score -= 600 * self.blocked.get(self._cell(i), 0)
            score += np.random.uniform(0, 60)
            if score > best:
                best, bi = score, i
        dx, dy = self._dirs()[bi]
        if self.step(dx, dy) < 60:
            self.blocked[self._cell(bi)] = self.blocked.get(self._cell(bi), 0) + 1

    def toward(self, target: tuple[float, float]) -> float:
        """One click toward a world target, bending around walls we stalled on. Returns remaining distance."""
        dx, dy = target[0] - self.pos[0], target[1] - self.pos[1]
        dist = math.hypot(dx, dy)
        ang = math.atan2(dy, dx)
        for bend in (0, 0.6, -0.6, 1.2, -1.2, 2.0, -2.0):
            a = ang + bend
            i = int(round(a / (2 * math.pi) * 12)) % 12
            if self.blocked.get(self._cell(i), 0) >= 2:
                continue
            r = min(dist, STEP * 1.5)
            if self.step(math.cos(a) * r, math.sin(a) * r) >= 60:
                return dist
            self.blocked[self._cell(i)] = self.blocked.get(self._cell(i), 0) + 1
        return dist

    def start(self) -> None:
        self.feats = features(self.bot.capture.grab())
        if not self.fix() and self.learn:
            self.chain.append((self._frame, (0.0, 0.0)))
            if not self.vmap.frames:  # the very first view: it is the map's origin
                self.vmap.add(self._frame, (0.0, 0.0))
                self.pos, self.chain = (0.0, 0.0), []


VIEW_C = (640, 360)  # the view centre: world (x, y) shows at VIEW_C + (x, y) - pos


def screen_of(w: Walker, target) -> tuple[int, int] | None:
    """Where a world point shows on screen now, if it's in the clickable box."""
    if w.pos is None:
        return None
    x, y = VIEW_C[0] + target[0] - w.pos[0], VIEW_C[1] + target[1] - w.pos[1]
    if BOX[0] <= x <= BOX[1] and BOX[2] <= y <= BOX[3]:
        return int(x), int(y)
    return None


def open_by_map(bot: Controller, w: Walker, target, state: str = "wp_menu") -> bool:
    """Click the target where the map says it is on screen (template-free: she may be standing on it) and
    wait for its panel."""
    w.fix()
    pt = screen_of(w, target)
    if pt is None:
        return False
    return click_open(bot, pt, state)


def click_open(bot: Controller, pt, state: str, tries=((0, 0), (0, -15))) -> bool:
    for dx, dy in tries:
        bot.click(pt[0] + dx, pt[1] + dy)
        t0 = bot.clock()
        while bot.clock() - t0 < 2.0:
            bot.kill.sleep(0.2)
            if bot.observe() == state:
                return True
    return False


def walk_to_target(bot: Controller, vmap: ViewMap, name: str, state: str = "wp_menu", walk=(),
                   max_steps: int = 25, seen=None) -> None:
    """Walk to the map target `name` and click it until its panel (`state`) opens. Off the map (a spawn the
    map hasn't seen): the `walk` clicks, then random steps, until a view is recognised."""
    if name not in vmap.targets:
        raise BotError(f"town map {vmap.root.name}: no target {name!r}")
    target = tuple(vmap.targets[name])
    w = Walker(bot, vmap)
    w.start()
    wi = 0
    for i in range(max_steps):
        pt = seen() if seen else None  # its template on screen: the surest click
        if pt is not None and click_open(bot, pt, state, ((0, 0), (0, -10), (10, 0))):
            log.info("town map: %s open (template) after %d steps", name, i)
            return
        if w.pos is None and not w.fix():
            if wi < len(walk):
                bot.click(*walk[wi])
                wi += 1
                w._track()
            else:
                w.step(*w._dirs()[np.random.randint(12)])
            continue
        if screen_of(w, target) is not None and open_by_map(bot, w, target, state):
            log.info("town map: %s open after %d steps", name, i)
            return
        log.info("town map: at (%.0f, %.0f), %s %.0f px away", w.pos[0], w.pos[1], name,
                 math.hypot(target[0] - w.pos[0], target[1] - w.pos[1]))
        w.toward(target)
        if i % 3 == 2:
            w.fix()  # correct the dead reckoning now and then
    bot.save_failure(f"townmap_{name}_not_reached")
    raise BotError(f"town map: {name} not opened in {max_steps} steps")
