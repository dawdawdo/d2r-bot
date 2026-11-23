"""Repair at Hratli now (dev helper), whichever act the game spawns in.

  python tools/repair_now.py

New Hell game -> to Act 3 if needed -> Hratli: Repair All (no keys) -> save & exit. For long tool sessions (finders,
probes) that don't run the run loop's repair schedule.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import leave_other_act, repair_at_hratli, restart_in_act3, spawn_act  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    ok = False
    try:
        for attempt in range(2):
            ensure_main_menu(bot)
            create_game(bot, cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
            act = spawn_act(bot)
            if act == 4:
                restart_in_act3(bot)
            elif act != 3:
                leave_other_act(bot, act)
            ok = repair_at_hratli(bot, keys=False)
            save_and_exit(bot)
            if ok:
                break
        print("repaired" if ok else "repair failed", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
