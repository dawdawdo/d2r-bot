"""Live test of the learned Ancient Tunnels entrance (bot/tunnels.py): new game -> Lost City WP -> war cries ->
Trap Door -> inside -> frame + automap frame to maps/<route>/tunnels_auto/arrivals/ -> ALWAYS save & exit.

  python tools/goto_tunnels.py --games 3
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import to_durance2  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import cast_warcries  # noqa: E402
from bot.tunnels import to_tunnels  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1)
    args = ap.parse_args()
    s = start_session()  # backs up saves
    cfg = s.cfg
    out = ROOT / "maps" / cfg["game"]["route"] / "tunnels_auto" / "arrivals"
    out.mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    ok = 0
    try:
        for n in range(args.games):
            t0 = time.time()
            try:
                to_durance2(bot, say=lambda m: print(f"game {n + 1}: {m}", flush=True), dest="wp_lost_city", merc=True)
                cast_warcries(bot)
                bot.deadline = bot.clock() + 180
                to_tunnels(bot)
                stamp = time.strftime("%m%d-%H%M%S")
                cv2.imwrite(str(out / f"{stamp}.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
                ok += 1
                print(f"game {n + 1}: inside after {time.time() - t0:.0f} s (HP {bot.hp:.0f}%)", flush=True)
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                bot.deadline = None
                bot.guard(False)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
        print(f"{ok}/{args.games} inside", flush=True)
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
