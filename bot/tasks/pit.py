"""The Pit (Act 1, Tamoe Highland; Hell area level 85, same white-Archon-Plate odds per kill as the Ancient Tunnels with weaker
monsters; Stephen chose to try it 2026-11-14). Outer Cloister waypoint -> blind lead-in teleports through the Monastery Gate into
Tamoe Highland -> the entrance the finder recorded -> clear Level 1 (the tunnels' loop: explore/tour, fight, loot).

Ready when maps/<route>/pit_auto/route.json exists:
  {"dest": "wp_outer_cloister", "pre": "-340,200,10;0,290,5", "search": "pit_tamoe2", "style": "gray",
   "inside_style": "tunnel", "goal": "pit_level_1"}
`search` is the finder's folder (tools/find_tunnels.py); its warp with dest == goal is the entrance.
Until then a requested "pit" falls back to LK in the run loop.
"""
from __future__ import annotations

import json
import logging

from ..config import ROOT
from ..controller import BotError, Controller
from . import Task

log = logging.getLogger(__name__)


def route_file(cfg: dict):
    return ROOT / "maps" / cfg["game"]["route"] / "pit_auto" / "route.json"


class Pit(Task):
    name = "pit"
    act = 3
    enter_wp = "wp_outer_cloister"
    a1_start = True  # Pit games end in Act 1: the next one spawns in the Rogue Encampment

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        f = route_file(cfg)
        self.route = json.loads(f.read_text()) if f.exists() else None

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return route_file(cfg).exists()

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..durance import AutomapOdometer, StopGraph, Walker, area_is, ensure_automap, take_warp, use_style
        from ..nav import CENTER, TP_SETTLE, frame_lag, in_play
        from ..town import act1_to, act4_to, cast_warcries, town_to_wp

        r = self.route
        if r is None:
            raise BotError("the Pit route isn't built yet")
        bot.keep_vendor_potions = True
        if not chained:
            act = getattr(bot, "act", 3)
            if act == 1:
                act1_to(bot, r["dest"])
            elif act == 4:
                act4_to(bot, r["dest"], area=None)
            else:
                town_to_wp(bot, r["dest"], None, stow=stow)
        bot.wait_still(timeout=3)
        bot.deadline = bot.clock() + self.cfg.get("pit", {}).get("timeout_s", 420)
        cast_warcries(bot)
        bot.cries_at = bot.clock()
        for seg in r["pre"].split(";"):  # the same landings every game from the waypoint arrival
            dx, dy, n = (int(v) for v in seg.split(","))
            dx, dy = in_play(dx, dy)
            for _ in range(n):
                bot.check()
                bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
                bot.sleep(TP_SETTLE + frame_lag(bot) + 0.15)
        bot.sleep(0.6)
        fold = ROOT / "maps" / self.cfg["game"]["route"] / r["search"]
        g = StopGraph.load(fold / "graph.json")
        w = next((x for x in g.warps if x.get("dest") == r["goal"]), None)
        if w is None:
            raise BotError("the Pit entrance isn't in the search graph")
        use_style(r["style"])
        try:
            odo = AutomapOdometer.load(fold, ensure_automap(bot))
            walker = Walker(bot, odo, g, fold, scan=False)
            if not walker.go(w["world"], tol=250, max_hops=25):
                bot.save_failure("pit_not_near_entrance")
                raise BotError(f"couldn't get near the Pit entrance (at {odo.pos.round().tolist()})")
            for attempt in range(3):
                door = {**w, "dest": None, "tries": attempt, "precise": True}
                if take_warp(bot, odo, g, door, fold, here=lambda b: area_is(b.capture.grab(), "tamoe_highland"),
                             goal=r["goal"]):
                    break
            else:
                bot.save_failure("pit_entrance_failed")
                raise BotError("Pit entrance: not inside after 3 tries")
        finally:
            use_style(r.get("inside_style", "tunnel"))
        log.info("inside the Pit (HP %.0f%% MP %.0f%%)", bot.hp or 0, bot.mp or 0)

    def farm(self, bot: Controller) -> dict:
        from ..tunnels import farm_tunnels

        r = self.route
        fold = ROOT / "maps" / self.cfg["game"]["route"] / "pit_auto"
        return farm_tunnels(bot, timeout_s=self.cfg.get("pit", {}).get("farm_s", 240),
                            style=r.get("inside_style", "tunnel"), folder=fold)
