"""Run bot steps by name against the live game (dev helper).

  python tools/do.py cast_buffs walk_route
  python tools/do.py "walk_route:4"      # first 4 legs only

Steps: cast_buffs, walk_route[:N], heal_at_ormus, save_and_exit, create_game, ensure_main_menu,
town_to_lower_kurast, recover_corpse.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import lifecycle, town  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        for step in sys.argv[1:]:
            t0 = time.perf_counter()
            name, _, arg = step.partition(":")
            if name == "walk_route":
                legs = cfg["town"]["route"][: int(arg)] if arg else cfg["town"]["route"]
                town.walk_route(bot, legs)
            elif name == "create_game":
                lifecycle.create_game(bot, cfg["game"]["difficulty"])
            elif hasattr(town, name):
                getattr(town, name)(bot)
            else:
                getattr(lifecycle, name)(bot)
            print(f"done {step} in {time.perf_counter() - t0:.1f}s")
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
