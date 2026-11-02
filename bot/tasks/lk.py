"""Lower Kurast super chests (phase 1): town -> waypoint -> LK -> the route's bonfire camps.

New games spawn in Act 3 (Kurast Docks, ~12 s walk to the WP) or, after a clean run that ended through
the LK waypoint, in Act 4 (Pandemonium Fortress, 1.6 s from the WP): see town.py "Act 4 starts".
With a next task in the same game (Mephisto), the run ends at the LK waypoint -> that task's waypoint.
"""
from __future__ import annotations

from ..controller import Controller
from ..lk import fingerprint_ok, leave_to_act4, leave_via_wp, load_route, run_route
from ..town import act4_to, town_to_lower_kurast
from . import Task


class LowerKurast(Task):
    name = "lk"
    act = 3
    enter_wp = "wp_lower_kurast"

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.route = load_route(cfg["game"]["route"])

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        arrived = lambda: fingerprint_ok(bot, self.route)  # noqa: E731
        if chained:
            bot.wait_still(timeout=5)
        elif getattr(bot, "act", 3) == 4:  # one_run sends A4 spawns that need the stash back to Act 3
            act4_to(bot, "wp_lower_kurast", arrived_check=arrived)
        else:
            town_to_lower_kurast(bot, arrived_check=arrived, stow=stow)

    def farm(self, bot: Controller) -> dict:
        from ..lk import TerrorZone, terrorized

        if self.cfg["game"].get("skip_terror", True) and terrorized(bot.capture.grab()):
            raise TerrorZone("Lower Kurast is terrorized this hour")
        bot.deadline = bot.clock() + self.cfg["safety"]["run_timeout_s"]  # the farming part only
        return run_route(bot, self.route, end=lambda odo, stats: self._end(bot, odo, stats))

    def _end(self, bot: Controller, odo, stats: dict) -> None:
        """Hand off to the next task's waypoint; else leave through Act 4 unless the next game needs
        Act 3 anyway (stash, vendors)."""
        if self.next is not None and self.next.enter_wp:
            stats["chained"] = leave_via_wp(bot, self.route, odo, "wp_tab_act3", self.next.enter_wp)
            return
        if not self.cfg["game"].get("act4_exit") or town_due(bot, stats):
            return
        stats["act4"] = leave_to_act4(bot, self.route, odo)


def town_due(bot: Controller, stats: dict) -> bool:
    """Will the next game need the Act 3 town? Loot to stash (anything but rejuvs and keys: extra key
    stacks are dropped at the A4 spawn), keys to buy, a repair due (set by the run loop)."""
    if any(p not in ("rejuv", "key") for p in stats.get("picked", [])):
        return True
    keys_min = bot.cfg["town"]["keys_min"]
    if bot.keys_left is None or bot.keys_left - getattr(bot, "keys_used", 0) <= keys_min:
        return True
    return bool(getattr(bot, "repair_next", False))
