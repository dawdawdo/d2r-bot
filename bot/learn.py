"""Learn a Lower Kurast map: explore from the waypoint, find the bonfire camps, verify their chests,
write a route (maps/<name>/route.yaml). The groundwork for relearning after a map change and for
map hunting (docs/roadmap.md).

Every super-chest camp has the same layout around its bonfire (lk.BONFIRE_LAYOUT), so learning a
map = finding bonfire world positions. World coords are odometry from the LK waypoint arrival view,
as in nav.py; every game starts there, so exploration can resume across games (explore.json).
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np

from .controller import Controller

log = logging.getLogger(__name__)

CELL = (400, 200)       # explore grid: about one teleport hop (nav.MAX_HOP x MAX_HOP_Y)
LIMIT = (12, 20)        # |cell index| bounds: LK is ~ +-4000 x +-3000 px around the waypoint
WP_EXCLUDE = 450        # px around the waypoint: its braziers look like bonfires
FIRE_MERGE = 350        # px: sightings closer than this are the same fire
SELF_RADIUS = 150       # px around the character: her own spell/hit glows read as flames
MAX_FAILS = 2           # a cell we failed to reach this often is treated as unreachable


class Explorer:
    """Grid frontier exploration state (pure logic, no I/O)."""

    def __init__(self) -> None:
        self.visited: set[tuple[int, int]] = set()
        self.fails: dict[tuple[int, int], int] = {}
        self.fires: list[dict] = []  # {"x", "y", "n", "area", "cells"}: running mean of a fire's world position

    @staticmethod
    def cell(pos) -> tuple[int, int]:
        return int(round(pos[0] / CELL[0])), int(round(pos[1] / CELL[1]))

    @staticmethod
    def center(c) -> tuple[float, float]:
        return float(c[0] * CELL[0]), float(c[1] * CELL[1])

    def mark_visited(self, pos) -> None:
        self.visited.add(self.cell(pos))

    def fail(self, target) -> None:
        c = self.cell(target)
        self.fails[c] = self.fails.get(c, 0) + 1

    def frontier(self) -> list[tuple[int, int]]:
        out = set()
        for cx, cy in self.visited:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = (cx + dx, cy + dy)
                    if (c not in self.visited and self.fails.get(c, 0) < MAX_FAILS
                            and abs(c[0]) <= LIMIT[0] and abs(c[1]) <= LIMIT[1]):
                        out.add(c)
        return sorted(out)

    def next_target(self, pos) -> tuple[float, float] | None:
        """Nearest frontier cell center in hops; ties go to the cell nearest the waypoint (explore
        outward in rings rather than down one long corridor)."""
        fr = self.frontier()
        if not fr:
            return None
        here = self.cell(pos)  # distance in hops (cells), not px: cells are 2:1 like the hop limits
        best = min(fr, key=lambda c: (math.hypot(c[0] - here[0], c[1] - here[1]), math.hypot(*c)))
        return self.center(best)

    def add_fires(self, pos, fires_screen, center=(640, 330)) -> None:
        """Bonfire-sized fires seen from world `pos` (screen x, y, area) -> merged world sightings."""
        for x, y, area in fires_screen:
            if math.hypot(x - center[0], y - center[1]) < SELF_RADIUS:
                continue
            wx, wy = pos[0] + x - center[0], pos[1] + y - center[1]
            if math.hypot(wx, wy) < WP_EXCLUDE:
                continue
            for f in self.fires:
                if math.hypot(f["x"] - wx, f["y"] - wy) < FIRE_MERGE:
                    f["x"] = (f["x"] * f["n"] + wx) / (f["n"] + 1)
                    f["y"] = (f["y"] * f["n"] + wy) / (f["n"] + 1)
                    f["n"] += 1
                    f["area"] = max(f["area"], area)
                    if list(self.cell(pos)) not in f.setdefault("cells", []):
                        f["cells"].append(list(self.cell(pos)))
                    break
            else:
                self.fires.append({"x": wx, "y": wy, "n": 1, "area": area, "cells": [list(self.cell(pos))]})

    def bonfires(self, min_seen: int = 2) -> list[tuple[float, float]]:
        """Fires seen from at least `min_seen` grid cells (flames in a fight are seen many times
        from one spot: spells, burning monsters)."""
        return [(round(f["x"]), round(f["y"])) for f in self.fires if len(f.get("cells", [])) >= min_seen]

    def to_dict(self) -> dict:
        return {"visited": sorted(self.visited), "fails": [[*c, n] for c, n in sorted(self.fails.items())],
                "fires": self.fires}

    @classmethod
    def from_dict(cls, d: dict) -> "Explorer":
        e = cls()
        e.visited = {tuple(c) for c in d.get("visited", [])}
        e.fails = {(a, b): n for a, b, n in d.get("fails", [])}
        e.fires = list(d.get("fires", []))
        return e

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1))

    @classmethod
    def load(cls, path: Path) -> "Explorer":
        return cls.from_dict(json.loads(path.read_text())) if path.exists() else cls()


def explore(bot: Controller, odo, ex: Explorer, max_hops: int = 120, debug_dir: Path | None = None,
            on_frame=None, find_bonfires: bool = True) -> str:
    """Teleport to the nearest unexplored cell until done, out of hops, or odometry is lost.
    Returns "done", "budget" or "lost". The caller saves & exits (never idle outside town).
    `on_frame(frame, pos)` sees the view at every stop (scouting other areas); `find_bonfires=False` skips
    the bonfire search (LK only)."""
    from .nav import BONFIRE_AREA, find_fires, teleport_to

    hops0 = getattr(bot, "hops", 0)
    while True:
        bot.check()
        frame = bot.capture.grab()
        odo.update(frame)
        if odo.lost:
            return "lost"
        ex.mark_visited(odo.pos)
        if on_frame is not None:
            on_frame(frame, odo.pos)
        if not find_bonfires:
            t = ex.next_target(odo.pos)
            if t is None:
                return "done"
            if getattr(bot, "hops", 0) - hops0 >= max_hops:
                return "budget"
            if not teleport_to(bot, odo, t, tol=150, max_hops=4, quiet=True):
                ex.fail(t)
            continue
        fires = [f for f in find_fires(frame) if f[2] >= BONFIRE_AREA]
        ex.add_fires(odo.pos, fires)
        if fires and debug_dir is not None:  # review what counted as a bonfire
            import cv2

            debug_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_dir / f"fire_{int(odo.pos[0])}_{int(odo.pos[1])}.jpg"),
                        cv2.resize(frame, None, fx=0.5, fy=0.5))
        t = ex.next_target(odo.pos)
        if t is None:
            return "done"
        if getattr(bot, "hops", 0) - hops0 >= max_hops:
            return "budget"
        if not teleport_to(bot, odo, t, tol=150, max_hops=4, quiet=True):
            ex.fail(t)


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def plan_route(bonfires: list[tuple[float, float]], layout: dict) -> list[dict]:
    """Route `bonfires` entries: the camp order and per-camp chest order with the shortest total
    teleport path from the waypoint (brute force: a map has only a few camps)."""
    from itertools import permutations

    stands = [{k: (b[0] + v["stand"][0], b[1] + v["stand"][1]) for k, v in layout.items()} for b in bonfires]
    best, best_len = None, float("inf")
    for camps in permutations(range(len(bonfires))):
        pos, total, plan = (0.0, 0.0), 0.0, []
        for ci in camps:  # each camp: best slot order from where we are (exact within the camp)
            orders = [o for o in permutations(stands[ci]) if _order_ok(o)]
            sl = min(orders, key=lambda o: _path_len(pos, [stands[ci][k] for k in o]))
            total += _path_len(pos, [stands[ci][k] for k in sl])
            pos = stands[ci][sl[-1]]
            plan.append((ci, list(sl)))
        if total < best_len:
            best, best_len = plan, total
    return [{"name": f"camp{i + 1}", "world": [int(bonfires[ci][0]), int(bonfires[ci][1])], "order": order}
            for i, (ci, order) in enumerate(best or [])]


ORDER_BEFORE = [("nw", "nw_deep")]  # nw_deep's drops land as labels over the nw chest (2026-10-27)


def _order_ok(order) -> bool:
    return all(a not in order or b not in order or order.index(a) < order.index(b) for a, b in ORDER_BEFORE)


def _path_len(start, pts) -> float:
    total, pos = 0.0, start
    for p in pts:
        total, pos = total + _dist(pos, p), p
    return total


FP_REGION = [520, 290, 240, 140]  # same crop as the hand route's fingerprint


def to_lk(bot: Controller):
    """Main menu -> Hell game -> Lower Kurast; returns a fresh odometer at the arrival view."""
    from .lifecycle import create_game, ensure_main_menu
    from .nav import Odometer
    from .town import town_to_lower_kurast

    ensure_main_menu(bot)
    create_game(bot, bot.cfg["game"]["difficulty"])
    town_to_lower_kurast(bot)
    return Odometer(bot.capture.grab())


def _out_of_lk(bot: Controller) -> None:
    from .lifecycle import save_and_exit

    bot.deadline = None
    if bot.state != "main_menu":
        save_and_exit(bot)  # never idle outside town


def verify_camp(bot: Controller, odo, bonfire) -> dict:
    """Anchor on the bonfire, then hover each layout chest spot. Returns {slot: found}."""
    from .lk import BONFIRE_LAYOUT, open_chest
    from .nav import reanchor, teleport_to, world_to_screen

    out = {}
    if not reanchor(bot, odo, bonfire):
        log.warning("verify: no bonfire at %s", bonfire)
        return out
    for slot, lay in BONFIRE_LAYOUT.items():
        stand = (bonfire[0] + lay["stand"][0], bonfire[1] + lay["stand"][1])
        teleport_to(bot, odo, stand)
        bot.wait_still(timeout=1.0, settle=1, poll=0.05, min_wait=0.0)
        odo.update(bot.capture.grab())
        cx, cy = world_to_screen(odo, bonfire[0] + lay["chest"][0], bonfire[1] + lay["chest"][1])
        out[slot] = open_chest(bot, cx, cy, click=False) is not None
        log.info("verify %s %s: %s", bonfire, slot, "chest" if out[slot] else "no chest")
    return out


def explore_games(bot: Controller, mdir: Path, games: int, hops: int) -> Explorer:
    """Explore over up to `games` games (resumes explore.json). Stops early when the frontier is
    empty or two games in a row add fewer than 5 cells (what's left is unreachable)."""
    import cv2

    from .controller import BotError

    ex_path = mdir / "explore.json"
    ex = Explorer.load(ex_path)
    slow = 0
    for g in range(games):
        before, result = len(ex.visited), "error"
        try:
            odo = to_lk(bot)
            fp = mdir / f"lk_wp_{mdir.name}.png"
            if not fp.exists():
                x, y, w, h = FP_REGION
                mdir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(fp), bot.capture.grab()[y : y + h, x : x + w])
            bot.deadline = bot.clock() + 240
            result = explore(bot, odo, ex, max_hops=hops, debug_dir=mdir / "fires")
        except BotError as e:
            log.warning("explore game %d: %s", g + 1, e)
        finally:
            _out_of_lk(bot)
            ex.save(ex_path)
        log.info("explore game %d: %s; %d cells visited, %d frontier, bonfires %s", g + 1, result,
                 len(ex.visited), len(ex.frontier()), ex.bonfires())
        slow = slow + 1 if len(ex.visited) - before < 5 else 0
        if result == "done" or slow >= 2:
            break
    return ex


def verify_games(bot: Controller, mdir: Path, ex: Explorer) -> dict:
    """One game per unverified bonfire candidate; results in verified.json."""
    from .controller import BotError

    path = mdir / "verified.json"
    verified = json.loads(path.read_text()) if path.exists() else {}
    for bf in ex.bonfires():
        key = f"{bf[0]},{bf[1]}"
        if key in verified:
            continue
        try:
            odo = to_lk(bot)
            bot.deadline = bot.clock() + 120
            verified[key] = verify_camp(bot, odo, bf)
        except BotError as e:
            log.warning("verify %s: %s", bf, e)
        finally:
            _out_of_lk(bot)
        mdir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(verified, indent=1))
    return verified


def write_route(mdir: Path, verified: dict) -> dict | None:
    """Route from camps with >= 2 verified chest spots -> maps/<name>/route.yaml. None if no camps."""
    import yaml

    from .lk import BONFIRE_LAYOUT

    camps = [tuple(map(int, k.split(","))) for k, v in verified.items() if sum(v.values()) >= 2]
    if not camps:
        return None
    route = {"fingerprint": {"template": f"lk_wp_{mdir.name}.png", "region": FP_REGION,
                             "threshold": 0.6, "half_threshold": 0.5},
             "bonfires": plan_route(camps, BONFIRE_LAYOUT), "targets": []}
    mdir.mkdir(parents=True, exist_ok=True)
    (mdir / "route.yaml").write_text("# Learned by bot/learn.py\n" + yaml.safe_dump(route, sort_keys=False))
    return route


def learn_map(bot: Controller, name: str, games: int = 15, hops: int = 70) -> dict | None:
    """Explore, verify, write maps/<name>/route.yaml. Returns the route (None: no camps found)."""
    from .config import ROOT

    mdir = ROOT / "maps" / name
    ex = explore_games(bot, mdir, games, hops)
    route = write_route(mdir, verify_games(bot, mdir, ex))
    log.info("learned map %s: %s", name, [c["world"] for c in route["bonfires"]] if route else "no camps")
    return route
