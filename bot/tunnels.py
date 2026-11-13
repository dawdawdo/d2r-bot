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
        use_style("tunnel")  # inside: dungeon automap lines (durance.automap_pixels)
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
# 2026-11-13 11:20 death: 58 casts emptied her mana (no Energy Shield) and Battle Orders had run out (507 -> 345)
CAST_MIN_MP = 30       # % mana: below this, no more casting at a stop (teleport and the shield need it)
LEAVE_MP = 15          # % mana with no regen in sight: end the run (save & exit) rather than die
# 2026-11-13 chickens: a Plague Bearer's poison (HP down with MP still full) took her from 100 to 43 % in 5 s while
# she stood casting. Struck that hard -> stop casting, two hops away from the movers, carry on elsewhere.
EVADE_DROP = 20        # HP points lost during one stop's fight
EVADE_BELOW = 65       # % HP
ENTER_MIN_HP = 70      # % HP inside with an empty belt: below this the run ends (the next game heals at Ormus)


def tunnels_folder(cfg: dict) -> Path:
    return ROOT / "maps" / cfg["game"]["route"] / "tunnels_auto"


class Struck(Exception):
    """Lost too much life while fighting at a stop: get away (carries the movers seen last)."""

    def __init__(self, movers) -> None:
        super().__init__("struck")
        self.movers = movers


def engage(bot) -> int:
    """Cast at moving monsters near her until two quiet looks in a row. Returns casts. Raises Struck."""
    import math
    import time

    from .nav import CENTER, movers

    sk = bot.cfg["hotkeys"]["skills"]
    casts, quiet, last_bliz, sel = 0, 0, 0.0, None
    hp0 = bot.hp or 100
    try:
        for _ in range(ENGAGE_ROUNDS):
            bot.check()
            if (bot.mp or 100) < CAST_MIN_MP:
                break
            m = [t for t in movers(bot, min_area=350) if OWN_RADIUS < math.dist(t[:2], CENTER) < REACH]
            hp = bot.hp or 100
            # struck = a big drop here, or low with monsters near. (14:47-16:25 "low AND still dropping" kept her fighting
            # below 65 %: ~40 % clean runs vs ~75 % before; arriving low is handled by ENTER_MIN_HP instead)
            if hp < hp0 - EVADE_DROP or (hp < EVADE_BELOW and m):
                raise Struck(m)
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


def evade(bot, odo, m, walker=None, visited=()) -> None:
    """Get away from a pack: back to a spot she already stood on (open and cleared; 2026-11-13 12:59 the "away
    from the movers" hops hit a wall four times and she didn't move), else two hops away from the movers' centre,
    turning 90 degrees when blocked."""
    import math

    import numpy as np

    from .nav import CENTER, hop

    start = odo.pos.copy()
    back = [v for v in reversed(list(visited)) if math.dist(v, start) >= 350]
    if walker is not None and back:
        walker.go(back[0], tol=150, max_hops=3)
    if math.dist(odo.pos, start) < 150:
        c = np.mean([t[:2] for t in m], axis=0) - CENTER if m else odo.pos.copy()
        d = -c / max(math.hypot(*c), 1e-6) * 320
        for turn in (0, 90, -90):
            r = math.radians(turn)
            step = np.array([d[0] * math.cos(r) - d[1] * math.sin(r), d[0] * math.sin(r) + d[1] * math.cos(r)])
            before = odo.pos.copy()
            hop(bot, odo, *step)
            if odo.lost and not odo.relocate(bot.capture.grab(), [before]):
                raise BotError("automap fix lost")
            if math.dist(odo.pos, before) >= 120:
                hop(bot, odo, *step)
                if odo.lost and not odo.relocate(bot.capture.grab(), [odo.pos]):
                    raise BotError("automap fix lost")
                break
    log.info("tunnels: struck -> evaded %d movers %s -> %s (HP %.0f%%)", len(m), start.round().tolist(),
             odo.pos.round().tolist(), bot.hp or 0)


def map_open(frame) -> bool:
    """Automap open inside the tunnels? The area name (top right) shows only then: edge match 0.99 vs ~0.4. Line-pixel
    counts misled here (2026-11-13 15:05: poison effects + lit stone = 11.4k "line" px with the map off)."""
    from .durance import area_is

    return area_is(frame, "ancient_tunnels")


def ensure_map(bot):
    """Automap on (by the area name); returns the frame showing it. BotError if it won't show."""
    for _ in range(3):
        f = bot.capture.grab()
        if map_open(f):
            return f
        bot.press("tab")
        bot.kill.sleep(0.45)
    f = bot.capture.grab()
    if map_open(f):
        return f
    bot.save_failure("tunnels_map_wont_show")
    raise BotError("automap won't show")


def loot_here(bot) -> list[str]:
    """Automap off (its lines clutter the labels), Alt-scan and pick, automap back on."""
    from .lk import loot

    if map_open(bot.capture.grab()):
        bot.press("tab")
        bot.kill.sleep(0.25)
    bot.input.move(1270, 590)  # park the cursor: resting on an urn, its hover name read as a white label (2026-11-13)
    bot.kill.sleep(0.15)
    bot.frame = bot.capture.grab()
    picked = loot(bot, max_picks=12)  # gold piles split into amount + word read as white "gem" labels and use picks up (gold is welcome: merc revives)
    ensure_map(bot)
    return picked


def tour_targets(g, visited: list, pos) -> list:
    """Known stops at least TOUR_SPACING from everywhere she has been this game."""
    import math

    return [s["pos"] for s in g.stops
            if all(math.dist(s["pos"], v) >= TOUR_SPACING for v in visited)]


def farm_tunnels(bot, timeout_s: float = 240) -> dict:
    """Inside the tunnels: explore / tour, fight, loot until the time is up or nothing is left to visit."""
    import math

    from .durance import AutomapOdometer, StopGraph, Walker, frontier, use_style

    from .vision.orbs import belt_slots

    bot.frame = bot.capture.grab()
    if (bot.hp or 100) < ENTER_MIN_HP and not any(belt_slots(bot.frame, bot.cfg["vision"]["belt"])):
        # 2026-11-13 14:28: a Lost City pack at the door took her to 52 %, no potions: 4 min of evading, then a chicken
        log.warning("tunnels: HP %.0f%% on arrival and the belt is empty: ending the run (Ormus next game)", bot.hp)
        return {"picked": [], "tunnel_stops": 0}
    use_style("tunnel")
    fold = tunnels_folder(bot.cfg)
    fold.mkdir(parents=True, exist_ok=True)
    odo = AutomapOdometer.load(fold, ensure_map(bot))
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
        from .town import cast_warcries

        refresh = bot.cfg["hotkeys"].get("warcry_refresh_s", 75)
        last_cries = bot.clock()  # cast on arrival in the Lost City
        calm = True
        while bot.clock() < end:
            if bot.clock() - last_cries > refresh:
                cast_warcries(bot)
                last_cries = bot.clock()
            if (bot.mp or 100) < LEAVE_MP:
                log.warning("tunnels: MP %.0f%%: ending the run", bot.mp)
                break
            try:
                if calm:  # right after an evade: keep moving, don't stand and fight where the pack can follow
                    casts += engage(bot)
                    picked += loot_here(bot)
                calm = True
            except Struck as e:
                try:
                    evade(bot, odo, e.movers, walker, visited)
                except BotError as err:
                    if type(err) is not BotError:
                        raise  # Chicken, Died, Danger, RunTimeout belong to the safety layer
                    log.warning("tunnels: %s while evading; ending the run here", err)
                    break
                calm = False
                continue  # loot later: the pack is where the drops are
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
            except BotError as e:  # "automap fix lost" (map toggled off, teleport-on-hit): map on, relocate, else stop
                if type(e) is not BotError or "fix lost" not in str(e):
                    raise  # Chicken, Died, Danger, RunTimeout: the safety layer's, never ours to swallow
                before = odo.pos.copy()
                try:
                    f = ensure_map(bot)
                    guesses = [before] + [v for v in reversed(visited)][:12] + [s_["pos"] for s_ in g.stops
                                                                               if math.dist(s_["pos"], before) < 1500]
                    if odo.relocate(f, guesses):
                        odo.lost = False
                        log.info("tunnels: fix recovered at %s after '%s'", odo.pos.round().tolist(), e)
                        continue
                except BotError:
                    pass
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
