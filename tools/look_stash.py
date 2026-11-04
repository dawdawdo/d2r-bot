"""Read-only look at the stash: new game -> walk to the stash -> save the shared and personal tabs -> save & exit.

  python tools/look_stash.py --out scratch/stash
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import open_stash, walk_chain, walk_route  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="scratch/stash")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    s = start_session(backup=True)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    b.window.set_client_size(*cfg["game"]["resolution"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        tcfg = cfg["town"]
        gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
        if gave_up is not None:
            walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
        if not open_stash(bot):
            return 1
        for name in ("shared_tab", "personal_tab"):
            bot.click(*cfg["stash"][name])
            bot.input.move(640, 650)
            bot.kill.sleep(0.5)
            cv2.imwrite(str(out / f"{name}.png"), b.capture.grab())
            if name == "shared_tab":
                for page in range(2, 6):
                    bot.click(*cfg["stash"]["shared_next_page"])
                    bot.input.move(640, 650)
                    bot.kill.sleep(0.5)
                    cv2.imwrite(str(out / f"shared_p{page}.png"), b.capture.grab())
        bot.press("esc")
        bot.kill.sleep(0.4)
    finally:
        try:
            save_and_exit(bot)
        finally:
            bot.release_all()
            s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
