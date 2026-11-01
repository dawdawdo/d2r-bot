"""Which key flips the automap opacity (Settings AutoMapFade 1 -> 2) when /players is typed?

  python tools/chat_fade_test.py

Main menu -> ensure_options (Center) -> Hell game -> types /players 1 via chat(), re-reads Settings;
then (if it flipped) resets and presses each key of the line alone, outside chat. Save & exit at the end.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.gamesettings import ensure_options, read_settings  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402

from bot.vision.screen import ScreenClassifier  # noqa: E402


def fade(cfg) -> int | None:
    time.sleep(0.6)  # D2R writes Settings.json right away
    return read_settings(cfg).get("AutoMapFade")


def main() -> int:
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        ensure_options(bot)
        print("fade at menu:", fade(cfg), flush=True)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        bot.sleep(1.0)
        print("fade in game:", fade(cfg), flush=True)
        for step in ("enter", "/", "p", "l", "a", "y", "e", "r", "s", "space", "1", "enter"):
            # the chat line one key at a time, with the chat box open
            if step == "enter" and bot.observe() != "in_game":
                bot.press("esc")
            bot.press(step)
            bot.kill.sleep(0.15)
            print(f"after {step!r} (in chat): fade {fade(cfg)}", flush=True)
        bot.sleep(1.0)
        print("after the line: fade", fade(cfg), flush=True)
    finally:
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
