"""Teleport in one direction from a waypoint and keep a view after every hop (automap on), then ALWAYS save & exit.
For following a hint like "from the Outer Cloister, teleport south-west, slightly more south than west" (Stephen,
2026-11-14: the Pit) and spotting the target in the frames.

  python tools/hop_probe.py --dest wp_outer_cloister --dx -230 --dy 330 --hops 14

Frames: maps/<route>/hop_probe/<time>/hop_NN.png (full) + sheet.jpg (all hops, small).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import to_durance2  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.nav import CENTER, TP_SETTLE, frame_lag, in_play  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import cast_warcries  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="wp_outer_cloister")
    ap.add_argument("--dx", type=int, default=-230)
    ap.add_argument("--dy", type=int, default=330)
    ap.add_argument("--hops", type=int, default=14)
    args = ap.parse_args()
    s = start_session()
    cfg = s.cfg
    cfg["safety"].update(chicken_hp_pct=40)
    out = ROOT / "maps" / cfg["game"]["route"] / "hop_probe" / time.strftime("%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    small = []
    try:
        to_durance2(bot, say=lambda m: print(m, flush=True), dest=args.dest, merc=True)
        cast_warcries(bot)
        bot.press("tab")  # automap on (the frames show it either way; it helps spot entrances)
        bot.sleep(1.0)
        dx, dy = in_play(args.dx, args.dy)
        for i in range(args.hops):
            bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
            bot.sleep(TP_SETTLE + frame_lag(bot) + 0.3)
            f = bot.capture.grab()
            cv2.imwrite(str(out / f"hop_{i:02d}.png"), f)
            sm = cv2.resize(f, (320, 180))
            cv2.putText(sm, str(i), (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            small.append(sm)
            print(f"hop {i}: HP {bot.hp}% MP {bot.mp}%", flush=True)
    except BotError as e:
        print(f"stopped: {e}", flush=True)
    finally:
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    if small:
        rows = [np.hstack(small[i : i + 4] + [np.zeros_like(small[0])] * (4 - len(small[i : i + 4])))
                for i in range(0, len(small), 4)]
        cv2.imwrite(str(out / "sheet.jpg"), np.vstack(rows))
    print(f"frames in {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
