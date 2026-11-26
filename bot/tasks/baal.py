"""Baal (Hell, Worldstone Chamber): waypoint Worldstone Keep Level 2 (Act V tab) -> the learned way to the Level 3
stairs (maps/<route>/wsk2_auto, found by tools/find_tunnels.py) -> Level 3 -> its stairs to the Throne of Destruction
(wsk3_auto) -> the throne room: Baal's five minion waves -> his portal -> the Worldstone Chamber -> Baal -> loot ->
save & exit.

Why him (Stephen 2026-11-26): Worusk's End, the Colossal Ancients statue only Baal drops (higher act bosses drop the
lower acts' statues, never the reverse), and Baal can drop anything. Andariel stays the SoJ target.

Town: the Rogue Encampment's stash, Akara, Kashya and Charsi, as Andariel (a1_town). Games end in Act 5, so the next
spawns in Harrogath: the run loop takes its waypoint to Act 1 first (town.act5_to_act1).

Ready when both levels' graphs hold a warp that reached the next level ("goal": true) and the throne fight is built.
"""
from __future__ import annotations

import logging

from ..controller import Controller
from . import Task
from .andariel import down_a_level, level_exit

log = logging.getLogger(__name__)

# (search folder, area here, area of the level the warp leads to)
LEVELS = [("wsk2_auto", "worldstone_keep_2", "worldstone_keep_3"),
          ("wsk3_auto", "worldstone_keep_3", "throne_of_destruction")]


class Baal(Task):
    name = "baal"
    act = 3
    enter_wp = "wp_worldstone_2"  # Act V tab (town.WP_TAB)
    needs_rejuvs = False
    vendor_potions = True
    min_free = 10
    needs_merc = True
    a1_town = True

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        from .. import baal

        return all(level_exit(cfg, f) for f, _, _ in LEVELS) and baal.READY

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..town import act1_to, act5_to

        bot.keep_vendor_potions = True
        if not chained:
            if getattr(bot, "act", 1) == 5:
                act5_to(bot, self.enter_wp)
            else:
                act1_to(bot, self.enter_wp)
        bot.wait_still(timeout=3)

    def farm(self, bot: Controller) -> dict:
        import time

        from .. import baal
        from ..town import cast_buffs, cast_warcries, set_players

        bcfg = self.cfg.get("baal", {})
        bot.deadline = bot.clock() + bcfg.get("timeout_s", 600)
        n = bcfg.get("players")
        if n and getattr(bot, "players_now", None) != n and set_players(bot, n):
            bot.players_now = n
        cast_warcries(bot)
        for k, (folder, here, goal) in enumerate(LEVELS):
            if k == len(LEVELS) - 1:
                cast_warcries(bot)
                cast_buffs(bot)
                bot.cries_at = time.time()
            down_a_level(bot, self.cfg, folder, here, goal)
            log.info("on %s (HP %.0f%% MP %.0f%%)", goal, bot.hp or 0, bot.mp or 0)
        return baal.throne(bot)
