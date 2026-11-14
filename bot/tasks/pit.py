"""The Pit (Act 1, Tamoe Highland; Hell area level 85, same white-Archon-Plate odds per kill as the Ancient Tunnels with weaker
monsters; Stephen chose to try it 2026-11-14). Waypoint Black Marsh -> Tamoe Highland -> "Pit Level 1" -> Level 2.

Not ready until the route is found (maps/<route>/pit_auto/route.json, written by the Pit finder, still to build).
Until then a requested "pit" falls back to LK in the run loop.
"""
from __future__ import annotations

from ..config import ROOT
from ..controller import BotError, Controller
from . import Task


def route_file(cfg: dict):
    return ROOT / "maps" / cfg["game"]["route"] / "pit_auto" / "route.json"


class Pit(Task):
    name = "pit"
    act = 3
    enter_wp = "wp_black_marsh"

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return route_file(cfg).exists()

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        raise BotError("the Pit route isn't built yet")

    def farm(self, bot: Controller) -> dict:
        raise BotError("the Pit route isn't built yet")
