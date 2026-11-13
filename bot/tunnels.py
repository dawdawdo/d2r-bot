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


# --- inside: explore, fight, loot ---------------------------------------------------------------------
# The tunnels' layout is fixed for this map, like Durance 2: the first games explore it (frontier of the
# automap canvas, maps/<route>/tunnels_auto/), later ones tour the known stops. At every stop: Blizzard /
# Glacial Spike at what moves, then Alt-scan and pick (lk.loot: the filter shows only wanted bases, runes, ...).
ENGAGE_ROUNDS = 10     # movers checks per stop
BLIZZARD_CD = 1.9      # s (Blizzard has a 1.8 s cooldown; Glacial Spike fills the gaps)
OWN_RADIUS = 70        # px around her: her own sprite and cast effects, not monsters
REACH = 520            # px: movers farther than this aren't worth standing for
TOUR_SPACING = 380     # world px between tour stops (one stop's view + loot reach covers about this)


def tunnels_folder(cfg: dict) -> Path:
    return ROOT / "maps" / cfg["game"]["route"] / "tunnels_auto"


def engage(bot) -> int:
    """Cast at moving monsters near her until two quiet looks in a row. Returns casts."""
    import math
    import time

    from .nav import CENTER, movers

    sk = bot.cfg["hotkeys"]["skills"]
    casts, quiet, last_bliz, sel = 0, 0, 0.0, None
    try:
        for _ in range(ENGAGE_ROUNDS):
            bot.check()
            m = [t for t in movers(bot, min_area=350) if OWN_RADIUS < math.dist(t[:2], CENTER) < REACH]
            if not m:
                quiet += 1
                if quiet >= 2:
                    break
                continue
            quiet = 0
            x, y, _ = min(m, key=lambda t: math.dist(t[:2], CENTER))  # the closest one is the threat
            want = "blizzard" if time.time() - last_bliz > BLIZZARD_CD else bot.cfg["hotkeys"]["attack"]
            if want != sel:
                bot.press(sk[want])
                sel = want
            bot.click(int(x), int(y), "right")
            if want == "blizzard":
                last_bliz = time.time()
            casts += 1
            bot.sleep(0.3)
    finally:
        if sel is not None:
            bot.press(sk["teleport"])
    return casts


def loot_here(bot) -> list[str]:
    """Automap off (its lines clutter the labels), Alt-scan and pick, automap back on."""
    from .durance import automap_shown, ensure_automap
    from .lk import loot

    if automap_shown(bot.capture.grab()):
        bot.press("tab")
        bot.kill.sleep(0.25)
    bot.frame = bot.capture.grab()
    picked = loot(bot, max_picks=6)
    ensure_automap(bot)
    return picked


def tour_targets(g, visited: list, pos) -> list:
    """Known stops at least TOUR_SPACING from everywhere she has been this game."""
    import math

    return [s["pos"] for s in g.stops
            if all(math.dist(s["pos"], v) >= TOUR_SPACING for v in visited)]


def farm_tunnels(bot, timeout_s: float = 240) -> dict:
    """Inside the tunnels: explore / tour, fight, loot until the time is up or nothing is left to visit."""
    import math

    from .durance import AutomapOdometer, StopGraph, Walker, ensure_automap, frontier, use_style

    use_style("tan")
    fold = tunnels_folder(bot.cfg)
    fold.mkdir(parents=True, exist_ok=True)
    odo = AutomapOdometer.load(fold, ensure_automap(bot))
    g = StopGraph.load(fold / "graph.json")

    def save() -> None:
        odo.save(fold)
        g.save(fold / "graph.json")

    walker = Walker(bot, odo, g, fold, save, scan=False)
    walker.arrive()
    end = bot.clock() + timeout_s
    picked: list[str] = []
    visited: list = []
    casts = stops = 0
    try:
        while bot.clock() < end:
            casts += engage(bot)
            picked += loot_here(bot)
            visited.append(odo.pos.copy())
            stops += 1
            targets = frontier(odo, g)
            mode = "explore"
            if not targets:
                targets, mode = tour_targets(g, visited, odo.pos), "tour"
            if not targets:
                log.info("tunnels: everything visited")
                break
            target = min(targets, key=lambda t: math.dist(t, odo.pos))
            try:
                reached = walker.go(target, tol=180, max_hops=8)
            except BotError as e:  # "automap fix lost" (teleport-on-hit, a jump): stop here, the caller saves & exits
                log.warning("tunnels: %s; ending the run here", e)
                break
            if not reached:
                g.failed.append([float(target[0]), float(target[1])])
                if mode == "tour":  # a known stop she can't reach from here this game: count it as seen
                    visited.append(list(target))
            save()
    finally:
        save()
    log.info("tunnels: %d stops, %d casts, picked %s", stops, casts, picked or "nothing")
    return {"picked": picked, "tunnel_stops": stops}
