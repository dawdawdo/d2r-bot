"""Back up saves, launch D2R if needed, and enter a Hell game (stays in town, for inspecting Blizzaga live).

  python tools/enter_town.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    s = start_session(backup=True)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.set_client_size(*cfg["game"]["resolution"])
    b.window.focus()
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        print("in game; client", b.capture.grab().shape)
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
