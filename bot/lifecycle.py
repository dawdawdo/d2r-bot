"""Game lifecycle (M2): main menu -> create game -> in town -> save & exit.

Screen states used (see config vision.states): title, main_menu, difficulty, loading,
in_game, esc_menu. Click points come from config `ui`.
"""
from __future__ import annotations

import logging

from .controller import BotError, Controller

log = logging.getLogger(__name__)

T_MENU = 20.0
T_LOAD = 45.0


def to_main_menu(bot: Controller) -> None:
    """From the title screen (or a menu) to the main menu."""
    state = bot.wait_for({"title", "main_menu", "in_game"}, T_LOAD)
    if state == "title":
        bot.press("space")
        bot.wait_for("main_menu", T_MENU)


def create_game(bot: Controller, difficulty: str = "hell") -> None:
    state = bot.wait_for({"title", "main_menu", "in_game"}, T_MENU)
    if state == "in_game":
        raise BotError("already in a game; expected main menu")
    if state == "title":
        to_main_menu(bot)
    bot.click_ui("play")
    bot.wait_for("difficulty", 10)
    bot.click_ui(f"difficulty_{difficulty}")
    bot.wait_for("in_game", T_LOAD)
    log.info("in game (%s)", difficulty)


def ensure_main_menu(bot: Controller) -> None:
    """Recover to the main menu from whatever state we're in (start of each run)."""
    state = bot.wait_for({"title", "main_menu", "in_game", "esc_menu", "difficulty"}, T_LOAD)
    if state == "title":
        to_main_menu(bot)
    elif state == "difficulty":
        bot.press("esc")
        bot.wait_for("main_menu", T_MENU)
    elif state == "esc_menu":
        bot.click_ui("save_and_exit")
        bot.wait_for("main_menu", T_LOAD)
    elif state == "in_game":
        save_and_exit(bot)


def save_and_exit(bot: Controller) -> None:
    for attempt in range(3):
        bot.press("esc")
        try:
            bot.wait_for("esc_menu", 3)
            break
        except BotError:
            if bot.state == "main_menu":
                return
            log.info("esc menu not up (attempt %d)", attempt + 1)
    else:
        raise BotError("could not open the esc menu")
    bot.click_ui("save_and_exit")
    bot.wait_for("main_menu", T_LOAD)
    log.info("back at main menu")
