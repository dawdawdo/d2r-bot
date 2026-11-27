"""Blessed Hammer (Smoked, Stephen's Hammerdin since 2026-11-27): stand still and cast.

Hammers spiral out from the caster wherever the click lands, so the fight is "stand in the right spot and keep casting".
Blessed Hammer is his LEFT skill (config profiles.Smoked hotkeys.hammer: left): shift + left click casts it in place
without walking. Concentration has to be the RIGHT skill for its aura to work, so the fight selects it first and
puts Teleport back after.

Shift is held only for the click itself: Shift + a belt key gives that potion to the merc, and the safety layer
(bot.observe -> potions) presses belt keys between casts.
"""
from __future__ import annotations

import logging
from typing import Callable

from .controller import Controller

log = logging.getLogger(__name__)

CAST_S = 0.46  # one cast at his 54 % faster cast rate: 11 frames (0.44 s); a click during the animation is lost
AIM = (700, 300)  # a spot just right of and above the character (640, 330): not on him, his merc or the HUD


def select_aura(bot: Controller) -> None:
    hk = bot.cfg["hotkeys"]
    aura = hk.get("aura")
    if aura:
        bot.press(hk["skills"][aura])
        bot.sleep(0.08)


def hammer(bot: Controller, seconds: float, until: Callable[[Controller], bool] | None = None,
           aim: tuple[int, int] = AIM) -> int:
    """Cast Blessed Hammer in place for `seconds` (or until `until(bot)` is true, checked between casts). Vitals are
    read every cast (potions, chicken: Chicken / Died propagate). Returns the number of casts."""
    hk = bot.cfg["hotkeys"]
    select_aura(bot)
    casts = 0
    end = bot.clock() + seconds
    try:
        while bot.clock() < end:
            bot.observe()
            if until is not None and until(bot):
                break
            bot.input.key_down("shift")
            try:
                bot.click(*aim, "left", hover=0)
            finally:
                bot.input.key_up("shift")
            casts += 1
            bot.sleep(CAST_S)
    finally:
        bot.press(hk["skills"]["teleport"])
    return casts
