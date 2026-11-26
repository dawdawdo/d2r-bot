"""The Throne of Destruction and Baal (bot/tasks/baal.py gets her here from Worldstone Keep Level 3).

Plan (to build from live probes of the throne room, which has a fixed layout):
1. From the Level 3 stairs, teleport into the throne room to a standing spot below-left of the throne, clear it.
2. Waves: Baal sends five (Colenzo, Achmel, Bartuc, Ventar, Lister, each with minions) one after another, each when the
   last is dead, at the same spot in front of the throne. Blizzard that spot, keep distance, chicken as usual.
3. After the fifth wave Baal leaves for the Worldstone Chamber: a portal opens right of the throne. Take it.
4. Baal: Blizzard + Glacial Spike from range, the boss bar for his life, loot with take_all (statues, essences).

Not built yet: READY stays False so the task isn't offered.
"""
from __future__ import annotations

import logging

from .controller import BotError, Controller

log = logging.getLogger(__name__)

READY = False


def throne(bot: Controller) -> dict:
    raise BotError("the Baal fight isn't built yet (bot/baal.py)")
