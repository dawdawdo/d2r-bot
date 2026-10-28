"""Mephisto (Hell, Durance of Hate Level 3): waypoint Durance 2 -> the learned path to the Level 3
stairs (bot/durance.py, found by tools/find_durance.py) -> moat trick -> kill -> loot -> save & exit.

Not ready until the stairs are found: maps/<route>/durance2_auto/route.json.
"""
from __future__ import annotations

import json

from ..config import ROOT
from ..controller import BotError, Controller
from ..town import act4_to, town_to_wp
from . import Task


def route_file(cfg: dict):
    return ROOT / "maps" / cfg["game"]["route"] / "durance2_auto" / "route.json"


class Mephisto(Task):
    name = "meph"
    act = 3
    enter_wp = "wp_durance_2"

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        f = route_file(cfg)
        self.route = json.loads(f.read_text()) if f.exists() else None

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return route_file(cfg).exists()

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        if chained:
            pass
        elif getattr(bot, "act", 3) == 4:
            act4_to(bot, self.enter_wp, area=None)
        else:
            town_to_wp(bot, self.enter_wp, None, stow=stow)
        bot.wait_still(timeout=3)

    def farm(self, bot: Controller) -> dict:
        if self.route is None:
            raise BotError("no Durance 2 route yet (tools/find_durance.py)")
        raise BotError("Mephisto: Level 3 not built yet")
