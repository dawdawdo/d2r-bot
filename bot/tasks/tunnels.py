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


def empty_columns(bot: Controller) -> int:
    """Belt columns with no potion (the visible bottom row reads empty)."""
    from ..vision.orbs import belt_kinds

    return sum(k is None for k in belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"]))


class AncientTunnels(Task):
    name = "tunnels"
    act = 3
    enter_wp = "wp_lost_city"
    a2_start = True  # games end in the tunnels, so the next spawns in Lut Gholein: its waypoint leads here too

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        from ..tunnels import entrance

        return entrance(cfg) is not None

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..town import act4_to, cast_warcries, town_to_wp
        from ..tunnels import to_tunnels

        bot.keep_vendor_potions = True  # restock_belt must not drink the healing potions bought for this task
        if not chained and getattr(bot, "act", 3) == 3 and empty_columns(bot) >= 1:
            from ..lifecycle import create_game, save_and_exit
            from ..town import buy_mana_at_ormus

            # healing potions into the empty belt columns (Stephen 2026-11-13; the rejuv stash is dry). The walk
            # to Ormus leaves her far from the waypoint: fresh game after, as Meph's mana stop does
            log.info("tunnels: %d empty belt columns -> healing potions at Ormus", empty_columns(bot))
            if not buy_mana_at_ormus(bot, fill="healing") and empty_columns(bot) >= 4:
                from .. import state

                # nothing bought at all: no gold on her (2026-11-13 18:59, deaths took it). town_to_wp withdraws from
                # the shared stash when this is set; the next game's stop buys
                log.warning("tunnels: no potions bought (no gold?): withdrawing from the stash this game")
                state.save({**state.load(), "gold_needed": True})
            save_and_exit(bot)
            create_game(bot, self.cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
        if not chained:
            if getattr(bot, "act", 3) == 2:
                from ..town import act2_to

                act2_to(bot, self.enter_wp)
            elif getattr(bot, "act", 3) == 4:
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
