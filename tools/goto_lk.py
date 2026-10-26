"""Dev helper: from anywhere -> new Hell game -> Lower Kurast, then stop (stay in game).

  python tools/goto_lk.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import heal_at_ormus, needs_heal, recover_corpse, town_to_lower_kurast  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        recover_corpse(bot)
        if needs_heal(bot):  # life carries over between games (same as bot.run)
            print(f"HP {bot.hp:.0f}% -> heal at Ormus, fresh game")
            heal_at_ormus(bot)
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
        town_to_lower_kurast(bot)
    finally:
        bot.release_all()
        s.close()
    print("in Lower Kurast")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
