"""Ancient Tunnels (Hell, area level 85): Archon Plates for Enigma (Stephen needs four, 2026-11-13) and every
other elite base. Waypoint Lost City (Act II tab) -> the Trap Door the bot found (bot/tunnels.py) -> explore /
tour the tunnels, fight, loot -> save & exit.

Not ready until the entrance is known: a warp with dest "ancient_tunnels" in maps/<route>/lost_city_auto/graph.json.
"""
from __future__ import annotations

import logging

from ..controller import Controller
from . import Task

log = logging.getLogger(__name__)


class AncientTunnels(Task):
    name = "tunnels"
    act = 3
    enter_wp = "wp_lost_city"

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        from ..tunnels import entrance

        return entrance(cfg) is not None

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..town import act4_to, cast_warcries, town_to_wp
        from ..tunnels import to_tunnels

        if not chained:
            if getattr(bot, "act", 3) == 4:
                act4_to(bot, self.enter_wp, area=None)
            else:
                town_to_wp(bot, self.enter_wp, None, stow=stow)
        bot.wait_still(timeout=3)
        bot.deadline = bot.clock() + self.cfg.get("tunnels", {}).get("timeout_s", 420)
        cast_warcries(bot)
        to_tunnels(bot)

    def farm(self, bot: Controller) -> dict:
        from ..tunnels import farm_tunnels

        tcfg = self.cfg.get("tunnels", {})
        return farm_tunnels(bot, timeout_s=tcfg.get("farm_s", 240))
