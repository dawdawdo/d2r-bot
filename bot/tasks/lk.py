"""Lower Kurast super chests (phase 1): Act 3 town -> waypoint -> LK -> the route's bonfire camps."""
from __future__ import annotations

from ..controller import Controller
from ..lk import fingerprint_ok, load_route, run_route
from ..town import town_to_lower_kurast
from . import Task


class LowerKurast(Task):
    name = "lk"
    act = 3

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        self.route = load_route(cfg["game"]["route"])

    def enter(self, bot: Controller, stow: bool = False) -> None:
        town_to_lower_kurast(bot, arrived_check=lambda: fingerprint_ok(bot, self.route), stow=stow)

    def farm(self, bot: Controller) -> dict:
        bot.deadline = bot.clock() + self.cfg["safety"]["run_timeout_s"]  # the farming part only
        return run_route(bot, self.route)
