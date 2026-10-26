"""Measure how fast teleports can be chained: from the LK waypoint, hop back and forth with
different settle times and count the hops that actually moved (odometry). Ends with save & exit.

  python tools/tp_rate.py [--settles 0.45,0.35,0.3,0.25,0.2] [--hops 10] [--dx 250]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import nav  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import recover_corpse, town_to_lower_kurast  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--settles", default="0.45,0.35,0.3,0.25,0.2")
    ap.add_argument("--hops", type=int, default=10)
    ap.add_argument("--dx", type=int, default=250)
    args = ap.parse_args()

    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    rows = []
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        recover_corpse(bot)
        town_to_lower_kurast(bot)
        odo = nav.Odometer(bot.capture.grab())
        for settle in map(float, args.settles.split(",")):
            nav.TP_SETTLE = settle
            moved = 0
            dist = []
            t0 = time.perf_counter()
            for i in range(args.hops):
                mx, _ = nav.hop(bot, odo, args.dx if i % 2 == 0 else -args.dx, 0)
                moved += abs(mx) > args.dx * 0.5
                dist.append(abs(mx))
            rows.append((settle, moved, (time.perf_counter() - t0) / args.hops))
            print(f"settle {settle:.2f}: {moved}/{args.hops} moved, {rows[-1][2]:.2f} s/hop, measured step median {sorted(dist)[len(dist) // 2]:.0f} px, lost={odo.lost}", flush=True)
    finally:
        try:
            if bot.state != "main_menu":
                save_and_exit(bot)
        finally:
            bot.release_all()
            s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
