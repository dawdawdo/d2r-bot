"""M3: Act 3 town (Kurast Docks) -> waypoint -> Lower Kurast.

New games always start at the same spot by Meshif's boat, and the town layout is fixed,
so we walk a recorded route (config town.route) and then locate the waypoint by template.
"""
from __future__ import annotations

import logging

import numpy as np

from .controller import BotError, Controller

log = logging.getLogger(__name__)


def _view_moved(a: np.ndarray, b: np.ndarray) -> bool:
    return float(np.abs(a[:560].astype(np.int16) - b[:560]).mean()) > 4


def walk_route(bot: Controller, route: list, retries: int = 2) -> None:
    """Click each leg in turn. If the view didn't move (click swallowed right after the game
    loads, or a wandering NPC was in the way), click the leg again."""
    for i, (x, y) in enumerate(route):
        for attempt in range(retries + 1):
            before = bot.capture.grab()
            bot.click(x, y)
            if not bot.wait_still(timeout=6):
                log.info("leg %d: view still moving after timeout", i)
            if _view_moved(before, bot.capture.grab()):
                break
            log.info("leg %d: didn't move (attempt %d), clicking again", i, attempt + 1)
            bot.kill.sleep(0.5)


def open_town_wp(bot: Controller, tcfg: dict) -> None:
    for attempt in range(3):
        loc = bot.find(tcfg["wp_template"], threshold=tcfg.get("wp_threshold", 0.7))
        if loc is None:
            bot.save_failure(f"town_wp_not_found_{attempt}")
            raise BotError("town waypoint not visible at end of route")
        ox, oy = tcfg["wp_click_offset"]
        bot.click(loc[0] + ox, loc[1] + oy)
        try:
            bot.wait_for("wp_menu", 5)
            return
        except BotError:
            log.info("waypoint menu didn't open (attempt %d)", attempt + 1)
    raise BotError("could not open the town waypoint")


def check_area(bot: Controller, template: str) -> bool:
    """True if the area name (shown top-right only while the automap is open) matches.

    Tab toggles the automap and we don't know its current state, so: check, toggle and
    check, toggle and check. On success the automap is open, so close it again.
    """
    for i in range(3):
        if i:
            bot.press("tab")
            bot.kill.sleep(0.4)
        if bot.find(template, region=(1100, 20, 180, 70), threshold=0.75) is not None:
            bot.press("tab")
            bot.kill.sleep(0.3)
            return True
    return False


def recover_corpse(bot: Controller) -> None:
    """After a death the corpse lies at the new-game spawn; clicking our own feet picks it up
    (harmless when there's no corpse)."""
    x, y = bot.cfg["town"]["corpse_click"]
    bot.click(x, y)
    bot.kill.sleep(0.8)
    bot.observe()


def _tooltip_points(bot: Controller, region, step: int = 30):
    """Yield hover points in `region` where a name tooltip pops up above the cursor."""
    import cv2

    rx, ry, rw, rh = region
    bot.input.move(1270, 590)
    bot.kill.sleep(0.15)
    base = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
    for y in range(ry, ry + rh, step):
        for x in range(rx, rx + rw, step):
            bot.input.move(x, y)
            bot.kill.sleep(0.07)
            g = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
            y0, x0 = max(0, y - 140), max(0, x - 120)
            if (np.abs(g[y0:y, x0 : x + 120] - base[y0:y, x0 : x + 120]) > 60).mean() > 0.02:
                yield x, y


def _name_points(bot: Controller, region, step: int = 30):
    """Yield hover points in `region` where an NPC/object name tooltip box appears."""
    from .vision.tooltip import find_tooltip

    rx, ry, rw, rh = region
    for y in range(ry, ry + rh, step):
        for x in range(rx, rx + rw, step):
            bot.input.move(x, y)
            bot.kill.sleep(0.08)
            if find_tooltip(bot.capture.grab(), x, y) is not None:
                yield x, y


def heal_at_ormus(bot: Controller) -> bool:
    """Walk toward the plaza, find Ormus by hover, talk to him (heals), close the dialog.
    The character ends up somewhere near Ormus, so the caller should start a new game."""
    tcfg = bot.cfg["town"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]])
    for attempt, (x, y) in enumerate(_tooltip_points(bot, tcfg["ormus_region"])):
        if attempt >= 4:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        if bot.find("npc_ormus.png", region=(0, 0, 1280, 500), threshold=0.8) is not None:
            bot.press("esc")
            log.info("healed by Ormus")
            return True
        bot.press("esc")  # someone else's dialog (or nothing); keep looking
        bot.kill.sleep(0.3)
    bot.save_failure("ormus_not_found")
    return False


def buy_keys(bot: Controller, h: dict) -> None:
    """Trade window open: Misc tab, shift+right-click the key = buy a stack (tops the inventory
    stack up; Stephen: keys ran out)."""
    bot.click(*h["misc_tab"])
    bot.kill.sleep(0.5)
    bot.input.key_down("shift")
    bot.kill.sleep(0.05)
    bot.click(*h["key"], "right")
    bot.kill.sleep(0.05)
    bot.input.key_up("shift")
    bot.kill.sleep(0.5)
    log.info("bought keys")


def repair_at_hratli(bot: Controller) -> bool:
    """From spawn: walk past Ormus, SE over the bridge, NE at the landing to Hratli's forge
    (route from Stephen, recorded 2026-10-26), open Trade/Repair, Repair All. Like the Ormus detour,
    this leaves us far from the WP, so the caller should start a new game."""
    tcfg = bot.cfg["town"]
    h = tcfg["hratli"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]] + h["route"])
    # Shape-based tooltip finder: the forge fire flickers, which fooled the frame-diff one.
    for attempt, (x, y) in enumerate(_name_points(bot, h["region"])):
        if attempt >= 5:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        loc = bot.find("npc_hratli.png", region=(0, 0, 1280, 500), threshold=0.8)
        if loc is None:
            bot.press("esc")  # someone else's dialog (or nothing); keep looking
            bot.kill.sleep(0.3)
            continue
        bot.click(loc[0] + h["trade_offset"][0], loc[1] + h["trade_offset"][1])
        for _ in range(10):
            bot.kill.sleep(0.3)
            if bot.find("trade_repair_all.png", region=(300, 460, 120, 100), threshold=0.8) is not None:
                break
        else:
            bot.save_failure("hratli_trade_not_opened")
            bot.press("esc")
            return False
        bot.click(*h["repair_all"])
        bot.kill.sleep(1.0)
        buy_keys(bot, h)
        bot.press("esc")
        bot.kill.sleep(0.5)
        log.info("repaired at Hratli")
        return True
    bot.save_failure("hratli_not_found")
    log.warning("Hratli not found; no repair")
    return False


def needs_heal(bot: Controller) -> bool:
    bot.observe()
    return bot.hp is not None and bot.hp < bot.cfg["town"]["heal_below_pct"]


def cast_buffs(bot: Controller) -> None:
    """Cast each buff (select it on right-click, right-click on ourselves), then put Teleport back."""
    hk = bot.cfg["hotkeys"]
    for name in hk.get("buffs", []):
        bot.press(hk["skills"][name])
        bot.kill.sleep(0.15)
        bot.click(*bot.cfg["town"]["corpse_click"], "right")
        bot.kill.sleep(0.7)
    bot.press(hk["skills"]["teleport"])
    bot.kill.sleep(0.15)


def open_stash(bot: Controller, attempts: int = 3) -> bool:
    """Click the stash chest (found by template; the route's end point varies by a few dozen px)
    and wait for its panel. An NPC (often Cain) standing on it eats the click and opens a dialog:
    close it with Esc and try again."""
    scfg = bot.cfg["stash"]
    for attempt in range(attempts):
        loc = bot.find("town_stash.png", region=(0, 0, 1280, 560), threshold=0.75)
        if loc is not None:
            x, y = loc[0] + 25, loc[1] + 28  # template is 50x48; click the chest's lower middle
        else:
            log.info("stash template not found; clicking the configured spot")
            x, y = scfg["click"]
        bot.click(x, y)
        for _ in range(12):
            bot.kill.sleep(0.3)
            if bot.find("stash_open.png", region=(165, 16, 110, 42), threshold=0.8) is not None:
                return True
        log.info("stash didn't open (attempt %d)", attempt + 1)
        bot.press("esc")  # close an NPC dialog if we clicked one
        bot.kill.sleep(1.0)
    bot.save_failure("stash_not_opened")
    log.warning("stash didn't open; skipping restock")
    return False


def restock_belt(bot: Controller) -> int:
    """If any visible belt slot is empty, open the stash (next to the town WP) and shift-click
    Full Rejuvenation Potions from the Materials tab until the belt row is full. Returns potions moved."""
    from .vision.orbs import belt_slots

    scfg = bot.cfg["stash"]
    belt = bot.cfg["vision"]["belt"]
    bot.observe()
    if all(belt_slots(bot.frame, belt)):
        return 0
    if not open_stash(bot):
        return 0
    bot.click(*scfg["materials_tab"])
    bot.kill.sleep(0.5)
    moved = 0
    for _ in range(scfg.get("max_potions", 16)):
        bot.input.move(1270, 590)
        bot.kill.sleep(0.15)
        if all(belt_slots(bot.capture.grab(), belt)):
            break
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(*scfg["full_rejuv"])
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.kill.sleep(0.3)
        moved += 1
    else:
        bot.observe()
        bot.save_failure("belt_not_full_after_restock")
        log.warning("belt still not full after %d clicks: stash out of Full Rejuvs?", moved)
    bot.press("esc")
    bot.kill.sleep(0.5)
    log.info("restocked belt with %d potions", moved)
    return moved


def town_to_lower_kurast(bot: Controller) -> None:
    tcfg = bot.cfg["town"]
    bot.wait_for("in_game", 10)
    cast_buffs(bot)
    walk_route(bot, tcfg["route"])
    restock_belt(bot)
    open_town_wp(bot, tcfg)
    bot.click_ui("wp_lower_kurast")
    try:  # the town frame lingers for a moment; wait for the load to actually start
        bot.wait_for("loading", 5, poll=0.05)
    except BotError:
        log.info("didn't catch the loading screen (fast load?)")
    bot.wait_for("in_game", 30)
    bot.guard(True)  # out of town from here on
    bot.wait_still(timeout=5)
    if not check_area(bot, "area_lower_kurast.png"):
        bot.save_failure("not_in_lower_kurast")
        raise BotError("arrived somewhere that isn't Lower Kurast")
    log.info("arrived in Lower Kurast")
