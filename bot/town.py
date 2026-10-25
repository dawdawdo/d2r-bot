"""M3: Act 3 town (Kurast Docks) -> waypoint -> Lower Kurast.

New games always start at the same spot by Meshif's boat, and the town layout is fixed,
so we walk a recorded route (config town.route) and then locate the waypoint by template.
"""
from __future__ import annotations

import logging

from .controller import BotError, Controller

log = logging.getLogger(__name__)


def walk_route(bot: Controller, route: list) -> None:
    for i, (x, y) in enumerate(route):
        bot.click(x, y)
        if not bot.wait_still(timeout=6):
            log.info("leg %d: view still moving after timeout", i)


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
    check, toggle and check. Leaves the automap open on success.
    """
    for i in range(3):
        if i:
            bot.press("tab")
            bot.kill.sleep(0.4)
        if bot.find(template, region=(1100, 20, 180, 70), threshold=0.75) is not None:
            return True
    return False


def town_to_lower_kurast(bot: Controller) -> None:
    tcfg = bot.cfg["town"]
    bot.wait_for("in_game", 10)
    walk_route(bot, tcfg["route"])
    open_town_wp(bot, tcfg)
    bot.click_ui("wp_lower_kurast")
    bot.wait_for("in_game", 30)
    bot.wait_still(timeout=5)
    if not check_area(bot, "area_lower_kurast.png"):
        bot.save_failure("not_in_lower_kurast")
        raise BotError("arrived somewhere that isn't Lower Kurast")
    log.info("arrived in Lower Kurast")
