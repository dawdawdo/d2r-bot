"""Live test of the learned route: new game -> WP Durance 2 -> Level 3 stairs -> save & exit.

  python tools/goto_level3.py --games 3
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
from bot.durance import STAIRS, AutomapOdometer, StopGraph, ensure_automap, to_durance2, to_level3  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3)
    args = ap.parse_args()

    s = start_session()  # backs up saves
    cfg = s.cfg
    maps = ROOT / "maps" / cfg["game"]["route"]
    auto = maps / "durance2_auto"
    ref = cv2.imread(str(maps / "durance2_route" / STAIRS["view"]))
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    g = StopGraph.load(auto / "graph.json")
    ok = 0
    try:
        for n in range(args.games):
            t0 = time.time()
            try:
                to_durance2(bot, say=lambda m: print(f"game {n + 1}: {m}", flush=True))
                bot.sleep(2.0)  # the "Entering ..." banner fades
                odo = AutomapOdometer.load(auto, ensure_automap(bot))
                t1 = time.time()
                to_level3(bot, odo, g, ref, auto)
                ok += 1
                print(f"game {n + 1}: Level 3 in {time.time() - t1:.1f}s from the WP", flush=True)
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                bot.guard(False)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            print(f"game {n + 1}: {time.time() - t0:.0f}s total", flush=True)
    finally:
        bot.release_all()
        s.close()
    print(f"{ok}/{args.games} reached Level 3", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
