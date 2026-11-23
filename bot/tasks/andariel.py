"""Andariel (Hell, Catacombs Level 4): waypoint Catacombs Level 2 (Act I tab) -> the learned way to the Level 3 stairs
(maps/<route>/cata2_auto, found by tools/find_tunnels.py) -> Level 3 -> its stairs (cata3_auto) -> Level 4 -> her
chamber -> Blizzard -> loot -> save & exit. Games end in Act 1, so the next one spawns at the Rogue Encampment waypoint.

Why her: D2R gives Andariel her quest drop on every kill (monstats: all her Hell treasure classes are Andarielq (H)),
2-3x Mephisto's rings: about 1 SoJ per 3,500 kills at 280 % MF, /players 1 (PROGRESS 2026-11-22 18:00). MF gate
mf.min.andy 200: her MF set (Shako, Chance Guards, Oculus, Gheed's; swapped in by tools/gear_swap.py 2026-11-23) reads 222 %.

Ready when both levels' graphs hold a warp that reached the next level ("goal": true).
"""
from __future__ import annotations

import logging

from ..config import ROOT
from ..controller import BotError, Controller
from . import Task

log = logging.getLogger(__name__)

# (search folder, area here, area of the level the warp leads to)
LEVELS = [("cata2_auto", "catacombs_2", "catacombs_3"), ("cata3_auto", "catacombs_3", "catacombs_4")]


def _folder(cfg: dict, name: str):
    return ROOT / "maps" / cfg["game"]["route"] / name


def level_exit(cfg: dict, folder: str) -> dict | None:
    """The warp of a search folder that led to the next level, if the finder has found it."""
    import json

    f = _folder(cfg, folder) / "graph.json"
    if not f.exists():
        return None
    g = json.loads(f.read_text())
    return next((w for w in g.get("warps", []) if w.get("goal") and w.get("dest") not in (None, "none")), None)


def short_path(g, a: int, b: int, max_edge: float = 800.0) -> list[int]:
    """Shortest stop path a -> b by distance over edges no longer than one long teleport (an edge recorded across a bad
    fix spans thousands of px). Falls back to [a, b]."""
    import heapq
    import math

    dist, prev, q = {a: 0.0}, {a: None}, [(0.0, a)]
    while q:
        d, u = heapq.heappop(q)
        if u == b:
            out = []
            while u is not None:
                out.append(u)
                u = prev[u]
            return out[::-1]
        if d > dist.get(u, 1e18):
            continue
        for v in g.edges.get(u, ()):
            e = math.dist(g.stops[u]["pos"], g.stops[v]["pos"])
            if e > max_edge or d + e >= dist.get(v, 1e18):
                continue
            dist[v], prev[v] = d + e, u
            heapq.heappush(q, (d + e, v))
    return [a, b]


def down_a_level(bot: Controller, cfg: dict, folder: str, here: str, goal: str) -> None:
    """From the arrival spot of a learned level, along the stop graph to its exit, and through it."""
    from ..durance import AutomapOdometer, StopGraph, Walker, area_is, ensure_automap, take_warp, use_style

    from ..town import inventory_panel

    inventory_panel(bot, False)  # a panel left up hides the automap's right half and the stairs label
    fold = _folder(cfg, folder)
    use_style("tunnel")
    g = StopGraph.load(fold / "graph.json")
    w = next((x for x in g.warps if x.get("goal") and x.get("dest") not in (None, "none")), None)
    if w is None:
        raise BotError(f"no {goal} exit learned in {folder}")
    odo = AutomapOdometer.load(fold, ensure_automap(bot))
    walker = Walker(bot, odo, g, fold, scan=False)
    start = g.nearest(odo.pos, within=1e9)
    for j in short_path(g, start, w["stop"])[1:]:
        # a leg that falls short isn't the end: the next stop is usually still reachable from where she landed
        # (2026-11-22: travel() gave up on the first missed leg 2,600 px from the exit)
        walker.go(g.stops[j]["pos"], tol=150, max_hops=5)
    if not walker.go(w["world"], tol=250, max_hops=10):  # take_warp makes its own last hops: try it anyway
        log.info("%s: not within 250 px of the exit (at %s)", folder, odo.pos.round().tolist())
    for attempt in range(3):
        door = {**w, "dest": None, "tries": attempt, "precise": True}
        if take_warp(bot, odo, g, door, fold, here=lambda b: area_is(ensure_automap(b), here), goal=goal):
            from ..lk import TerrorZone, terror_info, terrorized

            # "Entering The Catacombs Level 4 / Terrorized" banner, or "Terrorized: 93" in the area info: level 93
            # monsters took her from 100 to 48 % in 3 s (2026-11-22 21:43). The run loop waits for the zone to rotate.
            if cfg["game"].get("skip_terror", True) and (terrorized(bot.capture.grab()) or terror_info(ensure_automap(bot))):
                raise TerrorZone(f"{goal} is terrorized this hour")
            return
    bot.save_failure(f"{folder}_exit_failed")
    raise BotError(f"{folder}: still on {here} after 3 tries at the exit")


class Andariel(Task):
    name = "andy"
    act = 3
    enter_wp = "wp_catacombs_2"
    a1_start = True  # games end in Catacombs Level 4: the next one spawns in the Rogue Encampment
    # Blizzaga's rejuvs ran out building this (2026-11-22); like the tunnels it runs on Ormus healing + mana potions
    # (potion_stop, Act 3 games) instead of being swapped for LK while the stash is dry
    needs_rejuvs = False
    vendor_potions = True  # its belt holds Ormus healing potions: heal with those in town before hunting for Ormus
    min_free = 6  # inventory cells to go straight from the Act 1 spawn: her loot is small (rings, runes, gems, charms)
    a1_town = True  # stash, Akara, Kashya, Charsi in the Rogue Encampment: never Act 3 (Stephen 2026-11-23; bot/a1town.py)

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return all(level_exit(cfg, f) for f, _, _ in LEVELS)

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..town import act1_to, act4_to, town_to_wp

        bot.keep_vendor_potions = True  # drink the bought healing/mana potions in the fight (the tunnels/Pit do too;
        # 2026-11-22 21:11: "belt is empty" with 4 bought potions in the belt, chicken at Andariel's 47 %)
        if not chained:
            from .tunnels import potion_stop

            potion_stop(bot, self.cfg)  # Act 3 games with an empty belt column: Ormus potions first
            act = getattr(bot, "act", 3)
            if act == 1:
                act1_to(bot, self.enter_wp)
            elif act == 4:
                act4_to(bot, self.enter_wp, area=None)
            else:
                town_to_wp(bot, self.enter_wp, None, stow=stow)
        bot.wait_still(timeout=3)

    def farm(self, bot: Controller) -> dict:
        import time

        from ..andy import fight
        from ..town import cast_buffs, cast_warcries, set_players

        acfg = self.cfg.get("andy", {})
        bot.deadline = bot.clock() + acfg.get("timeout_s", 360)
        n = acfg.get("players")
        if n and getattr(bot, "players_now", None) != n and set_players(bot, n):
            bot.players_now = n  # the run loop sets LK's back next game
            from .. import state

            st = state.load()
            st.pop("players_window", None)  # as Meph: the next session must set its own again
            st["players_n"] = n
            state.save(st)
        cast_warcries(bot)
        for k, (folder, here, goal) in enumerate(LEVELS):
            if k == len(LEVELS) - 1:  # fresh for the fight (BO ~90 s), cast on Level 3: standing still at the Level 4
                cast_warcries(bot)    # stairs for them cost ~45 % life to her minions (2026-11-22 21:37)
                cast_buffs(bot)
                bot.cries_at = time.time()
            down_a_level(bot, self.cfg, folder, here, goal)
            log.info("on %s (HP %.0f%% MP %.0f%%)", goal, bot.hp or 0, bot.mp or 0)
        safety = self.cfg["safety"]
        saved = dict(safety)
        safety.update(acfg.get("safety", {}))
        try:
            out = fight(bot)
        finally:
            safety.clear()
            safety.update(saved)
        return out
