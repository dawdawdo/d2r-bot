"""Ancient Tunnels (Hell, area level 85: every elite base can drop, Archon Plate for Enigma).

Route: town -> waypoint Lost City (Act II tab) -> the Trap Door the bot found itself (tools/find_tunnels.py,
2026-11-13: northwest of the waypoint, world (-4952, -2978) px on the automap canvas) -> two clicks (the first
opens it: "Trap Door" 108 px -> "Ancient Tunnels" 161 px; the second goes down) -> inside.

The search state is maps/<route>/lost_city_auto/ (automap canvas + stop graph + warps). The warp marked
dest "ancient_tunnels" is the entrance; after a map change, rerun find_tunnels with --fresh.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import ROOT
from .controller import BotError

log = logging.getLogger(__name__)


def folder(cfg: dict) -> Path:
    return ROOT / "maps" / cfg["game"]["route"] / "lost_city_auto"


def entrance(cfg: dict) -> dict | None:
    f = folder(cfg) / "graph.json"
    if not f.exists():
        return None
    return next((w for w in json.loads(f.read_text())["warps"] if w.get("dest") == "ancient_tunnels"), None)


def in_tunnels(bot) -> bool:
    from .durance import area_is

    for i in range(3):
        if area_is(bot.capture.grab(), "ancient_tunnels"):
            return True
        bot.press("tab")  # the area name shows only with the automap open
        bot.kill.sleep(0.5)
    return False


def to_tunnels(bot) -> None:
    """From the Lost City waypoint arrival to inside the Ancient Tunnels. BotError if it can't."""
    from .durance import AutomapOdometer, StopGraph, Walker, area_is, ensure_automap, take_warp, use_style

    cfg = bot.cfg
    w = entrance(cfg)
    if w is None:
        raise BotError("no Ancient Tunnels entrance yet (tools/find_tunnels.py)")
    use_style("red")
    fold = folder(cfg)
    try:
        odo = AutomapOdometer.load(fold, ensure_automap(bot))
        g = StopGraph.load(fold / "graph.json")
        walker = Walker(bot, odo, g, fold, scan=False)
        goal = g.nearest(w["world"], within=600)
        if goal is not None:
            walker.travel(goal)
        if not walker.go(w["world"], tol=250, max_hops=20):
            bot.save_failure("tunnels_not_near_door")
            raise BotError(f"couldn't get near the Trap Door (at {odo.pos.round().tolist()})")
        for attempt in range(3):
            door = {**w, "dest": None, "tries": attempt, "precise": True}  # a copy: the search graph stays as is
            if take_warp(bot, odo, g, door, fold, here=lambda b: area_is(b.capture.grab(), "lost_city"),
                         goal="ancient_tunnels"):
                break
        else:
            bot.save_failure("tunnels_door_failed")
            raise BotError("Trap Door: not inside after 3 tries")
    finally:
        use_style("tan")  # inside: a dungeon automap like Durance's
    if not in_tunnels(bot):
        bot.save_failure("tunnels_not_inside")
        raise BotError("left the Lost City but not into the Ancient Tunnels")
    log.info("inside the Ancient Tunnels (HP %.0f%% MP %.0f%%)", bot.hp or 0, bot.mp or 0)
