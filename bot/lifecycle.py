"""Game lifecycle (M2): main menu -> create game -> in town -> save & exit.

Screen states used (see config vision.states): title, main_menu, difficulty, loading,
in_game, esc_menu. Click points come from config `ui`.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import cv2

from .controller import BotError, Controller
from .vision.screen import ASSETS

log = logging.getLogger(__name__)

T_MENU = 20.0
T_LOAD = 45.0
CHAR_LIST = (1030, 40, 220, 500)  # (x, y, w, h) of the character list on the main menu, client coords


def to_main_menu(bot: Controller) -> None:
    """From the title screen (or a menu) to the main menu."""
    state = bot.wait_for({"title", "main_menu", "in_game"}, T_LOAD)
    if state == "title":
        bot.press("space")
        bot.wait_for("main_menu", T_MENU)


def check_difficulty_button(bot: Controller, difficulty: str) -> None:
    """Before clicking: the button's label must be right under the click point. Entering another
    difficulty, even once, makes D2R regenerate the character's Hell map (Stephen's map with the
    learned route would be gone). Templates: bot/assets/templates/difficulty_<name>.png."""
    from .vision.screen import ASSETS

    if not (ASSETS / f"difficulty_{difficulty}.png").exists():
        return
    x, y = bot.cfg["ui"][f"difficulty_{difficulty}"]
    if bot.find(f"difficulty_{difficulty}.png", region=(x - 60, y - 25, 120, 50), threshold=0.8) is None:
        bot.save_failure(f"difficulty_{difficulty}_not_found")
        bot.press("esc")
        raise BotError(f"{difficulty} button not where expected; not clicking (a wrong difficulty resets the map)")


def find_character(frame, name: str, threshold: float = 0.8) -> tuple[int, int] | None:
    """Centre of `name`'s row in the main menu's character list (client coords), or None."""
    x, y, w, h = CHAR_LIST
    tpl = cv2.imread(str(ASSETS / f"char_{name}.png"))
    if tpl is None:
        return None
    _, score, _, at = cv2.minMaxLoc(cv2.matchTemplate(frame[y : y + h, x : x + w], tpl, cv2.TM_CCOEFF_NORMED))
    return (x + at[0] + tpl.shape[1] // 2, y + at[1] + tpl.shape[0] // 2) if score >= threshold else None


def select_character(bot: Controller) -> None:
    """Main menu: click the configured character. D2R opens on whoever was played last, and Stephen plays others
    (2026-11-04: Play put the bot on ThroatCutter). Not found = stop the session, never Play on a guess."""
    name = bot.cfg["game"]["character"]
    row = find_character(bot.capture.grab(), name)
    if row is None and "offline_tab" in bot.cfg.get("ui", {}):
        # started through Battle.net (GLaDOS), D2R opens on the Online tab: the offline characters are one tab over
        log.info("%s not in the list: trying the Offline tab", name)
        bot.click_ui("offline_tab")
        bot.kill.sleep(1.0)
        row = find_character(bot.capture.grab(), name)
    if row is None:
        bot.save_failure("character_not_found")
        bot.kill.trip(f"character {name} not found on the main menu")
        bot.kill.check()
    bot.click(*row)
    bot.kill.sleep(1.5)  # the 3D model swaps
    log.info("selected %s", name)


def newest_save(save_dir: Path) -> str | None:
    saves = list(Path(save_dir).glob("*.d2s"))
    return max(saves, key=lambda p: p.stat().st_mtime).stem if saves else None


def check_character(bot: Controller) -> None:
    """In game: D2R rewrites the character's .d2s on entering, so the newest one names who we're playing.
    Read only. The wrong character = leave at once and stop the whole session (the launcher stops too)."""
    want, have = bot.cfg["game"]["character"], newest_save(os.path.expandvars(bot.cfg["paths"]["save_dir"]))
    if have == want:
        return
    bot.save_failure("wrong_character")
    log.error("playing %s, not %s: leaving and stopping", have, want)
    save_and_exit(bot)
    bot.kill.trip(f"wrong character {have}, expected {want}")
    bot.kill.check()


def create_game(bot: Controller, difficulty: str = "hell") -> None:
    state = bot.wait_for({"title", "main_menu", "in_game"}, T_MENU)
    if state == "in_game":
        raise BotError("already in a game; expected main menu")
    if state == "title":
        to_main_menu(bot)
    select_character(bot)
    bot.click_ui("play")
    bot.wait_for("difficulty", 10)
    check_difficulty_button(bot, difficulty)
    bot.click_ui(f"difficulty_{difficulty}")
    bot.wait_for("in_game", T_LOAD)
    log.info("in game (%s)", difficulty)
    check_character(bot)


def ensure_main_menu(bot: Controller) -> None:
    """Recover to the main menu from whatever state we're in (start of each run)."""
    bot.guard(False)
    known = {"title", "main_menu", "in_game", "esc_menu", "difficulty"}
    deadline = bot.clock() + 90
    while True:  # right after launch: intro videos/splash screens -> press space to skip
        # D2R restores its saved window size late in startup, undoing the resize at launch (Stephen had
        # resized it while playing, 2026-11-06), and at another size nothing matches
        bot.window.set_client_size(*bot.cfg["game"]["resolution"])
        state = bot.observe()
        if state in known:
            break
        if bot.clock() > deadline:
            bot.save_failure("ensure_main_menu_stuck")
            raise BotError(f"stuck in state {state!r} trying to reach the main menu")
        if state == "unknown":
            bot.press("space")
        bot.kill.sleep(2.0)
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
    """Esc menu -> Save and Exit -> main menu. Sets bot.died_on_exit when the life orb was empty on the way
    out (a chicken that came too late: 2026-11-01 22:00 "You have died" behind a chicken; the corpse
    must be picked up next game)."""
    bot.guard(False)  # we're leaving; don't raise Chicken while trying to exit
    bot.died_on_exit = False
    for tries in range(2):
        for attempt in range(3):
            bot.press("esc")
            try:
                bot.wait_for("esc_menu", 3)
                break
            except BotError:
                if bot.state == "main_menu":
                    return
                if bot.hp is not None and bot.hp <= 1:
                    bot.died_on_exit = True
                log.info("esc menu not up (attempt %d)", attempt + 1)
        else:
            raise BotError("could not open the esc menu")
        bot.click_ui("save_and_exit")
        try:
            bot.wait_for("main_menu", 8)
            break
        except BotError:
            if bot.state != "in_game" or tries:
                bot.wait_for("main_menu", T_LOAD)  # still loading out
                break
            # the click did nothing (2026-11-01 21:31, after an Ormus miss: 45 s in town): again
            log.info("save & exit click didn't take; again")
    log.info("back at main menu")
