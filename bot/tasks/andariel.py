"""Andariel (Hell, Catacombs Level 4): waypoint Catacombs Level 2 (Act I tab) -> the learned way to the Level 3 stairs
(maps/<route>/cata2_auto, found by tools/find_tunnels.py) -> Level 3 -> its stairs (cata3_auto) -> Level 4 -> her
chamber -> Blizzard -> loot -> save & exit. Games end in Act 1, so the next one spawns at the Rogue Encampment waypoint.

Why her: D2R gives Andariel her quest drop on every kill (monstats: all her Hell treasure classes are Andarielq (H)),
2-3x Mephisto's rings: about 1 SoJ per 2,500 kills at 280 % MF, /players 3 (PROGRESS 2026-11-22 18:00). No MF gate yet
(Stephen 2026-11-22: he can't swap the MF gear in now; first runs go at 0 %). Add `andy` to mf.min once he has.

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


def down_a_level(bot: Controller, cfg: dict, folder: str, here: str, goal: str) -> None:
    """From the arrival spot of a learned level, along the stop graph to its exit, and through it."""
    from ..durance import AutomapOdometer, StopGraph, Walker, area_is, ensure_automap, take_warp, use_style

    fold = _folder(cfg, folder)
    use_style("tunnel")
    g = StopGraph.load(fold / "graph.json")
    w = next((x for x in g.warps if x.get("goal") and x.get("dest") not in (None, "none")), None)
    if w is None:
        raise BotError(f"no {goal} exit learned in {folder}")
    odo = AutomapOdometer.load(fold, ensure_automap(bot))
    walker = Walker(bot, odo, g, fold, scan=False)
    walker.travel(w["stop"])
    if not walker.go(w["world"], tol=250, max_hops=8):  # take_warp makes its own last hops: try it anyway
        log.info("%s: not within 250 px of the exit (at %s)", folder, odo.pos.round().tolist())
    for attempt in range(3):
        door = {**w, "dest": None, "tries": attempt, "precise": True}
        if take_warp(bot, odo, g, door, fold, here=lambda b: area_is(ensure_automap(b), here), goal=goal):
            return
    bot.save_failure(f"{folder}_exit_failed")
    raise BotError(f"{folder}: still on {here} after 3 tries at the exit")


class Andariel(Task):
    name = "andy"
    act = 3
    enter_wp = "wp_catacombs_2"
    a1_start = True  # games end in Catacombs Level 4: the next one spawns in the Rogue Encampment
    needs_rejuvs = True

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return all(level_exit(cfg, f) for f, _, _ in LEVELS)

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..town import act1_to, act4_to, town_to_wp

        if not chained:
            act = getattr(bot, "act", 3)
            if act == 1:
                act1_to(bot, self.enter_wp)
            elif act == 4:
                act4_to(bot, self.enter_wp, area=None)
            else:
                town_to_wp(bot, self.enter_wp, None, stow=stow)
        bot.wait_still(timeout=3)

    def farm(self, bot: Controller) -> dict:
        from ..town import cast_warcries

        bot.deadline = bot.clock() + self.cfg.get("andy", {}).get("timeout_s", 360)
        cast_warcries(bot)
        bot.cries_at = bot.clock()
        for folder, here, goal in LEVELS:
            down_a_level(bot, self.cfg, folder, here, goal)
            log.info("on %s (HP %.0f%% MP %.0f%%)", goal, bot.hp or 0, bot.mp or 0)
        raise BotError("Andariel's chamber: not built yet")  # Level 4 route + fight come once Level 4 is reached
