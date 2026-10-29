"""Durance of Hate Level 2: position from the automap, and a stop graph for finding the Level 3 stairs.

Why the automap: the dungeon is dark and the character's light circle moves with her, so screen
odometry drifts (docs/meph-navigation.md). The automap overlay (Tab) is drawn in thin tan lines over
the scene, unaffected by light, and shows far more of the level than the screen. Its scale is fixed
(~1/8 of the world: a 287 px hop moved it 36 px, live 2026-10-28).

AutomapOdometer keeps the average of every automap view seen (`canvas` = line hits / times in view
since the pixel first showed a line,
persisted across games: the map is fixed and every game starts at the waypoint) and places each new
view on it by phase correlation. Averaging lets torches, spells and monsters fade out; a plain union
filled up with them and stopped matching (live 2026-10-28).
That's an absolute fix, so errors don't add up over hops. It has the same interface as nav.Odometer
(pos, lost, resp, update), so nav.hop / nav.teleport_to work with it unchanged.

StopGraph: the places she has stood (world px from the waypoint arrival) and which hops connect them.
Exploration grows it; a run follows its shortest path from the waypoint to the stairs.
"""
from __future__ import annotations

import json
import logging
import math
from collections import deque
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)

SCALE = 16.0  # world px per canvas px: automap is ~1/8 of the world, the canvas is half-size on top
VIEW = (40, 0, 1240, 590)  # full-res screen area used (x, y, w, h): above the HUD, right of the portrait
# Screen boxes (full res) that never scroll with the map: portrait, area/time text, the character herself
STATIC = [(0, 0, 90, 85), (1040, 0, 240, 80), (590, 230, 110, 140)]
LIGHT = ((640, 290), (300, 200))  # ellipse (center, half axes) of her light circle, full res
BLOB = 4  # px: a BLOB x BLOB square fits inside firelight and lit floors, never inside an automap line
MIN_PIXELS = 1500  # mask pixels (full res) for "the automap is showing"; live: 7000-11000 in Durance 2
GOOD_RESP = 0.08   # phase-correlation peak for a trusted fix (live hops: 0.20-0.30)
HOP_GAIN = 1.17    # landing / commanded offset (nav.HOP_GAIN)


_LIGHT: np.ndarray | None = None


def _outside_light() -> np.ndarray:
    """0 inside her light circle: lit scenery there (wall statues, the WP) has the automap's tan color
    and moves 8x faster than the automap, which fooled the fix (live 2026-10-28)."""
    global _LIGHT
    if _LIGHT is None:
        _LIGHT = np.ones((720, 1280), np.uint8)
        cv2.ellipse(_LIGHT, LIGHT[0], LIGHT[1], 0, 0, 360, 0, -1)
    return _LIGHT


def automap_pixels(frame: np.ndarray) -> np.ndarray:
    """Binary mask (full res, uint8 0/1) of automap line pixels: desaturated tan, fairly bright."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = ((h >= 15) & (h <= 30) & (s >= 60) & (s <= 170) & (v >= 90)).astype(np.uint8)
    k = np.ones((BLOB, BLOB), np.uint8)
    m &= 1 - cv2.dilate(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), np.ones((7, 7), np.uint8))
    for x, y, w, hh in STATIC:
        m[y : y + hh, x : x + w] = 0
    m &= _outside_light()
    x, y, w, hh = VIEW
    out = np.zeros_like(m)
    out[y : y + hh, x : x + w] = m[y : y + hh, x : x + w]
    return out


def automap_shown(frame: np.ndarray) -> bool:
    return int(automap_pixels(frame).sum()) >= MIN_PIXELS


def view_mask(frame: np.ndarray) -> np.ndarray:
    """The automap view as the canvas sees it: VIEW area, half size, float32, slightly blurred."""
    x, y, w, h = VIEW
    m = automap_pixels(frame)[y : y + h, x : x + w].astype(np.float32)
    m = cv2.resize(m, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(m, (3, 3), 0.8)


_SEEN: np.ndarray | None = None


def seen_mask() -> np.ndarray:
    """1 where a view can show automap lines (VIEW minus static boxes and her light), half size."""
    global _SEEN
    if _SEEN is None:
        full = _outside_light().copy()
        for x, y, w, hh in STATIC:
            full[y : y + hh, x : x + w] = 0
        x, y, w, h = VIEW
        _SEEN = cv2.resize(full[y : y + h, x : x + w].astype(np.float32), (w // 2, h // 2),
                           interpolation=cv2.INTER_AREA)
    return _SEEN


class AutomapOdometer:
    """World position (px from the arrival spot) from automap views placed on a growing canvas."""

    def __init__(self, frame: np.ndarray | None = None, hits: np.ndarray | None = None,
                 seen: np.ndarray | None = None, origin=(0, 0)) -> None:
        self.dungeon = True
        self.pos = np.array([0.0, 0.0])
        self.lost = False
        self.resp = 1.0
        self.since_anchor = 0.0
        self.hits = hits if hits is not None else np.zeros((0, 0), np.float32)
        self.seen = seen if seen is not None else np.zeros((0, 0), np.float32)
        self.canvas = self._average(self.hits, self.seen)
        self.origin = np.array(origin, float)  # canvas px of the arrival view's top-left
        self.added = 0
        if frame is not None:
            if self.canvas.size:
                self.localize(view_mask(frame), np.zeros(2))
            else:
                self._add(view_mask(frame), np.zeros(2))

    # --- canvas ------------------------------------------------------------------------------
    @staticmethod
    def _average(hits: np.ndarray, seen: np.ndarray) -> np.ndarray:
        return np.divide(hits, seen, out=np.zeros_like(hits), where=seen > 0.5)

    def _ensure(self, tl: np.ndarray, shape) -> None:
        """Grow the canvas so a view at canvas top-left `tl` fits (with a margin)."""
        h, w = shape
        H, W = self.canvas.shape if self.canvas.size else (0, 0)
        if not self.canvas.size:
            self.canvas, self.hits, self.seen = (np.zeros((h + 200, w + 200), np.float32) for _ in range(3))
            self.origin = np.array([100.0, 100.0]) - tl + self.origin
            return
        x0, y0 = int(math.floor(tl[0])), int(math.floor(tl[1]))
        left, top = max(0, 100 - x0), max(0, 100 - y0)
        right, bottom = max(0, x0 + w + 100 - W), max(0, y0 + h + 100 - H)
        if left or top or right or bottom:
            self.canvas, self.hits, self.seen = (
                cv2.copyMakeBorder(a, top, bottom, left, right, cv2.BORDER_CONSTANT, value=0)
                for a in (self.canvas, self.hits, self.seen))
            self.origin += (left, top)

    def _tl(self, pos) -> np.ndarray:
        return self.origin + np.asarray(pos, float) / SCALE

    def _add(self, mask: np.ndarray, pos) -> None:
        self._ensure(self._tl(pos), mask.shape)
        x, y = np.round(self._tl(pos)).astype(int)
        h, w = mask.shape
        win = (slice(y, y + h), slice(x, x + w))
        # Count views only from a pixel's first line on: the automap shows a place only once she's
        # been near it, so the dark views before that say nothing about it.
        self.seen[win] += seen_mask() * ((self.hits[win] > 0.05) | (mask > 0.05))
        self.hits[win] += mask
        self.canvas[win] = self._average(self.hits[win], self.seen[win])
        self.added += 1

    def _crop(self, pos, shape) -> np.ndarray:
        self._ensure(self._tl(pos), shape)
        x, y = np.round(self._tl(pos)).astype(int)
        h, w = shape
        return self.canvas[y : y + h, x : x + w]

    def localize(self, mask: np.ndarray, guess) -> tuple[np.ndarray, float]:
        """Where is this view on the canvas, near `guess` (world)? Returns (world pos, response)."""
        guess = np.round(np.asarray(guess, float) / SCALE) * SCALE  # crop on whole canvas px
        crop = self._crop(guess, mask.shape)
        win = cv2.createHanningWindow(mask.shape[::-1], cv2.CV_32F)
        (dx, dy), resp = cv2.phaseCorrelate(crop, mask, win)
        return guess - np.array([dx, dy]) * SCALE, float(resp)

    # --- Odometer interface --------------------------------------------------------------------
    def update(self, frame: np.ndarray, expect=None) -> tuple[float, float]:
        mask = view_mask(frame)
        guesses = [self.pos]
        if expect is not None:
            guesses.insert(0, self.pos + np.asarray(expect, float) * HOP_GAIN)
        best = max((self.localize(mask, g) for g in guesses), key=lambda r: r[1])
        new, self.resp = best
        if self.resp < GOOD_RESP:
            if not self.lost:
                log.warning("automap fix weak (resp %.3f)", self.resp)
            self.lost = True
            return 0.0, 0.0
        self.lost = False
        moved = new - self.pos
        self.pos = new
        self.since_anchor += math.hypot(*moved)
        self._add(mask, self.pos)
        return float(moved[0]), float(moved[1])

    def relocate(self, frame: np.ndarray, guesses) -> bool:
        """Find ourselves again after a jump: try each guess (world), keep the best fix."""
        mask = view_mask(frame)
        new, resp = max((self.localize(mask, g) for g in guesses), key=lambda r: r[1])
        if resp < GOOD_RESP:
            return False
        self.pos, self.resp, self.lost = new, resp, False
        self._add(mask, self.pos)
        return True

    # --- persistence ---------------------------------------------------------------------------
    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(folder / "automap.png"), np.clip(self.canvas * 255, 0, 255).astype(np.uint8))  # to look at
        np.savez_compressed(folder / "automap.npz", hits=self.hits, seen=self.seen)
        (folder / "automap.json").write_text(json.dumps({"origin": self.origin.tolist(), "scale": SCALE}))

    @classmethod
    def load(cls, folder: Path, frame: np.ndarray | None = None) -> "AutomapOdometer":
        data, meta = folder / "automap.npz", folder / "automap.json"
        if not (data.exists() and meta.exists()):
            return cls(frame)
        with np.load(data) as d:
            hits, seen = d["hits"], d["seen"]
        return cls(frame, hits, seen, json.loads(meta.read_text())["origin"])


# --- stop graph --------------------------------------------------------------------------------
SAME_STOP = 130  # world px: landings closer than this to a known stop are that stop
# Where the automap draws HER (full-res screen px). The waypoint room's outline is drawn around the WP
# platform (~(655, 350) at arrival), and over 89 stops the revealed walls lie closest to the stops with
# (620-660, 360-400). The earlier (640, 500) was another room's outline: it put every frontier target
# ~1000 px too far south, so most of them were walls or void (live 2026-10-28).
AM_CHAR = (640, 370)


class StopGraph:
    def __init__(self) -> None:
        self.stops: list[dict] = [{"pos": [0.0, 0.0], "scanned": False}]  # 0 = waypoint
        self.edges: dict[int, set[int]] = {0: set()}
        self.warps: list[dict] = []   # long tooltips: {"stop", "screen", "world", "w", "crop", "dest", "tries"}
        self.failed: list[list[float]] = []  # frontier targets we couldn't reach

    def nearest(self, pos, within: float = SAME_STOP) -> int | None:
        best, bd = None, within
        for i, s in enumerate(self.stops):
            d = math.dist(s["pos"], pos)
            if d < bd:
                best, bd = i, d
        return best

    def add_stop(self, pos) -> int:
        self.stops.append({"pos": [float(pos[0]), float(pos[1])], "scanned": False})
        self.edges[len(self.stops) - 1] = set()
        return len(self.stops) - 1

    def link(self, a: int, b: int) -> None:
        if a != b:
            self.edges[a].add(b)
            self.edges[b].add(a)

    def path(self, a: int, b: int) -> list[int] | None:
        """Fewest-hops path a -> b (BFS)."""
        prev = {a: None}
        q = deque([a])
        while q:
            u = q.popleft()
            if u == b:
                out = []
                while u is not None:
                    out.append(u)
                    u = prev[u]
                return out[::-1]
            for v in sorted(self.edges[u]):
                if v not in prev:
                    prev[v] = u
                    q.append(v)
        return None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"stops": self.stops, "edges": {k: sorted(v) for k, v in self.edges.items()},
                                    "warps": self.warps, "failed": self.failed}, indent=1))

    @classmethod
    def load(cls, path: Path) -> "StopGraph":
        g = cls()
        if path.exists():
            d = json.loads(path.read_text())
            g.stops = d["stops"]
            g.edges = {int(k): set(v) for k, v in d["edges"].items()}
            g.warps = d.get("warps", [])
            g.failed = d.get("failed", [])
        return g


def canvas_to_world(odo: AutomapOdometer, cx: float, cy: float) -> tuple[float, float]:
    """Canvas px -> the world position she'd stand on for the automap to draw her there."""
    ox = (AM_CHAR[0] - VIEW[0]) / 2
    oy = (AM_CHAR[1] - VIEW[1]) / 2
    return (cx - odo.origin[0] - ox) * SCALE, (cy - odo.origin[1] - oy) * SCALE


FRONTIER_CELL = 16     # canvas px (256 world px)
FRONTIER_AWAY = 600    # world px from every stop
FRONTIER_FAILED = 400  # world px around a target we couldn't reach


def frontier(odo: AutomapOdometer, g: StopGraph) -> list[tuple[float, float]]:
    """Places the automap shows corridors (wall lines) but she hasn't stood near yet."""
    if not odo.canvas.size:
        return []
    c = FRONTIER_CELL
    H, W = odo.canvas.shape
    walls = (odo.canvas[: H // c * c, : W // c * c] > 0.3).astype(np.float32)  # seen as a line most times
    dens = walls.reshape(H // c, c, W // c, c).mean(axis=(1, 3))
    stops = np.array([s["pos"] for s in g.stops])
    out = []
    for cy, cx in zip(*np.nonzero(dens > 0.03)):
        w = canvas_to_world(odo, (cx + 0.5) * c, (cy + 0.5) * c)
        if np.min(np.hypot(*(stops - w).T)) < FRONTIER_AWAY:
            continue
        if any(math.dist(f, w) < FRONTIER_FAILED for f in g.failed):
            continue
        out.append(w)
    return out


# --- finding the Level 3 stairs (tools/find_durance.py) -----------------------------------------
# A level exit shows its destination's name when hovered ("Durance of Hate Level 3" / "... Level 1"),
# in a long tooltip; chests, doors and the waypoint have short ones ("Locked Chest" is 134-140 px).
WARP_MIN_W = 150
AREA_REGION = (1060, 20, 220, 70)  # area name, top right (shown while the automap is open)
SCAN_COVER = (430, 200)  # a scan covers about this much (world px) around where she stood
SCAN_ABORT = (10, 20)  # HP, MP points lost during a scan (Energy Shield drains MP first) -> stop scanning


def to_durance2(bot, say=print) -> None:
    """New Hell game -> (heal at Ormus if hurt: life carries over between games) -> WP Durance 2."""
    from .controller import BotError
    from .lifecycle import create_game, ensure_main_menu, save_and_exit
    from .town import act4_to, heal_at_ormus, needs_heal, recover_corpse, restart_in_act3, spawn_act, town_to_wp

    diff = bot.cfg["game"]["difficulty"]
    ensure_main_menu(bot)
    create_game(bot, diff)
    bot.wait_for("in_game", 10)
    recover_corpse(bot)
    act = spawn_act(bot)
    if needs_heal(bot):
        say(f"HP {bot.hp:.0f}% -> heal at Ormus, fresh game")
        if act == 4:
            restart_in_act3(bot)
        heal_at_ormus(bot)
        save_and_exit(bot)
        create_game(bot, diff)
        bot.wait_for("in_game", 10)
        act = 3
        if needs_heal(bot):  # Ormus not found: try again next game, don't go in hurt
            raise BotError(f"still at HP {bot.hp:.0f}% after Ormus")
    if act == 4:
        act4_to(bot, "wp_durance_2", area=None)
    else:
        town_to_wp(bot, "wp_durance_2", None)


def ensure_automap(bot) -> np.ndarray:
    from .controller import BotError

    for i in range(3):
        f = bot.capture.grab()
        if automap_shown(f):
            return f
        bot.press("tab")
        bot.kill.sleep(0.4)
    raise BotError("automap won't show")


def on_level2(bot) -> bool:
    return bot.find("area_durance_2.png", region=AREA_REGION, threshold=0.8) is not None


def scan_due(g: StopGraph, pos) -> bool:
    return not any(s["scanned"] and abs(s["pos"][0] - pos[0]) < SCAN_COVER[0]
                   and abs(s["pos"][1] - pos[1]) < SCAN_COVER[1] for s in g.stops)


def scan_warps(bot, odo: AutomapOdometer, g: StopGraph, stop: int, folder: Path) -> int:
    """Hover a coarse grid; record long tooltips (level exits) with their world position."""
    from .vision.tooltip import find_tooltip

    found = 0
    k = 0
    hp0, mp0 = bot.hp or 100, bot.mp or 100
    for y in range(80, 560, 90):
        for x in range(110, 1180, 120):
            k += 1
            if k % 6 == 0:
                bot.check()
                if (bot.hp or 100) < hp0 - SCAN_ABORT[0] or (bot.mp or 100) < mp0 - SCAN_ABORT[1]:
                    log.info("scan at stop %d stopped: struck (HP %.0f%% MP %.0f%%)", stop, bot.hp, bot.mp)
                    bot.input.move(1270, 590)
                    return found  # standing still is what gets her hurt: move on, scan here another time
            bot.input.move(x, y)
            bot.kill.sleep(0.08)
            f = bot.capture.grab()
            box = find_tooltip(f, x, y, half_w=230, max_w=420)
            if box is None or box[2] < WARP_MIN_W:
                continue
            world = [float(odo.pos[0] + x - 640), float(odo.pos[1] + y - 330)]
            if any(math.dist(w["world"], world) < 250 for w in g.warps):
                continue
            bx, by, bw, bh = box
            name = f"warps/tt_{len(g.warps)}.png"
            (folder / "warps").mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(folder / name), f[by : by + bh, bx : bx + bw])
            g.warps.append({"stop": stop, "screen": [x, y], "world": world, "w": int(bw), "crop": name,
                            "dest": None, "tries": 0})
            log.info("long tooltip (%d px) at stop %d, world %s -> %s", bw, stop, [round(v) for v in world], name)
            found += 1
    bot.input.move(1270, 590)
    g.stops[stop]["scanned"] = True
    return found


class Walker:
    """Hops toward targets and keeps the stop graph up to date on the way (new stops get a
    thumbnail and, where no scan has covered the view yet, a tooltip scan)."""

    def __init__(self, bot, odo: AutomapOdometer, g: StopGraph, folder: Path, save=lambda: None,
                 scan: bool = True) -> None:
        self.bot, self.odo, self.g, self.folder, self.save, self.scan = bot, odo, g, folder, save, scan
        self.cur = g.nearest(odo.pos, within=300) or 0
        self.hops = 0

    def arrive(self) -> None:
        g, odo = self.g, self.odo
        j = g.nearest(odo.pos)
        new = j is None
        if new:
            j = g.add_stop(odo.pos)
        g.link(self.cur, j)
        self.cur = j
        if new:
            log.info("stop %d at %s", j, odo.pos.round().tolist())
            (self.folder / "thumbs").mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(self.folder / "thumbs" / f"{j}.jpg"),
                        cv2.resize(self.bot.capture.grab()[:590], None, fx=0.25, fy=0.25,
                                   interpolation=cv2.INTER_AREA))
        if self.scan and scan_due(g, odo.pos):
            scan_warps(self.bot, odo, g, j, self.folder)
            self.save()

    def go(self, target, tol: float = 220, max_hops: int = 10) -> bool:
        """Teleport toward world `target`, sideways when blocked. True when within `tol`."""
        from .controller import BotError
        from .nav import MAX_HOP, MAX_HOP_Y, hop

        target = np.asarray(target, float)
        stuck = 0
        for _ in range(max_hops):
            self.bot.check()
            d = target - self.odo.pos
            if math.hypot(*d) <= tol:
                return True
            step = d / HOP_GAIN
            step *= min(1.0, MAX_HOP / max(math.hypot(*step), 1e-6), MAX_HOP_Y / max(abs(step[1]), 1e-6))
            if stuck:
                ang = [60, -60, 110, -110][(stuck - 1) % 4]
                c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                step = np.array([c * step[0] - s * step[1], s * step[0] + c * step[1]])
                step *= min(1.0, MAX_HOP_Y / max(abs(step[1]), 1e-6))
            before = self.odo.pos.copy()
            hop(self.bot, self.odo, *step)
            self.hops += 1
            if self.odo.lost:
                guesses = [s["pos"] for s in self.g.stops if math.dist(s["pos"], before) < 2500]
                if not self.odo.relocate(self.bot.capture.grab(), [before] + guesses):
                    raise BotError("automap fix lost")
            if math.dist(self.odo.pos, before) < 80:
                stuck += 1
                if stuck > 4:
                    return False
                continue
            stuck = 0
            self.arrive()
        return math.dist(self.odo.pos, target) <= tol

    def travel(self, target_stop: int) -> bool:
        """Follow the stop graph to a known stop."""
        for nxt in (self.g.path(self.cur, target_stop) or [self.cur, target_stop])[1:]:
            if not self.go(self.g.stops[nxt]["pos"], tol=110, max_hops=5):
                return False
        return True


def take_warp(bot, odo: AutomapOdometer, g: StopGraph, w: dict, folder: Path) -> bool:
    """Click a level exit; record where it leads (top-right area name crop). True if we left Level 2."""
    from .nav import world_to_screen

    w["tries"] = w.get("tries", 0) + 1
    x, y = world_to_screen(odo, *w["world"])
    x, y = int(np.clip(x, 60, 1220)), int(np.clip(y, 40, 560))
    bot.click(x, y)
    bot.sleep(3.0)
    if on_level2(bot):
        log.info("warp %s: still on Level 2 after clicking (%d, %d)", w["crop"], x, y)
        if w["tries"] >= 2:
            w["dest"] = "none"
        return False
    i = g.warps.index(w)
    f = bot.capture.grab()
    x0, y0, ww, hh = AREA_REGION
    cv2.imwrite(str(folder / f"warps/dest_{i}.png"), f[y0 : y0 + hh, x0 : x0 + ww])
    cv2.imwrite(str(folder / f"warps/dest_{i}_view.jpg"), cv2.resize(f, None, fx=0.5, fy=0.5))
    w["dest"] = f"warps/dest_{i}.png"
    tmpl = Path(__file__).parent / "assets" / "templates" / "area_durance_3.png"
    w["level3"] = (bot.find("area_durance_3.png", region=AREA_REGION, threshold=0.8) is not None
                   if tmpl.exists() else None)
    log.info("warp %d leads somewhere else (level 3: %s); saved %s", i, w["level3"], w["dest"])
    return True


def explore_game(bot, odo: AutomapOdometer, g: StopGraph, folder: Path, max_hops: int = 60,
                 save=lambda: None) -> str:
    """One game of stairs hunting from the waypoint. Returns why it stopped: "warp" (took an exit),
    "hops", "done" (no frontier left). BotError (fix lost, safety) propagates."""
    walker = Walker(bot, odo, g, folder, save)
    walker.arrive()
    while walker.hops < max_hops:
        todo = [w for w in g.warps if w.get("dest") is None]
        if todo:
            w = todo[0]
            walker.travel(w["stop"])
            if take_warp(bot, odo, g, w, folder):
                save()
                return "warp"
            continue
        targets = frontier(odo, g)
        if not targets:
            return "done"
        target = min(targets, key=lambda t: math.dist(t, odo.pos))
        log.info("frontier: %d targets; going to %s (%d px)", len(targets), [round(v) for v in target],
                 math.dist(target, odo.pos))
        if not walker.go(target):
            g.failed.append([float(target[0]), float(target[1])])
        save()
    return "hops"
