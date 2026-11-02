"""Walk a town by clicks and save a half-size frame after each (for finding another act's waypoint).

  python tools/town_probe.py --clicks "1000,150 1000,150 900,200"   # screen points, one walk each

New Hell game (wherever she spawns) -> click, wait, frame -> ... -> save & exit.
Frames: fixtures/raw/town_probe/<nn>.jpg (+ full-size <nn>.png).
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
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clicks", default="")
    ap.add_argument("--wait", type=float, default=2.5)
    args = ap.parse_args()
    s = start_session()
    cfg = s.cfg
    out = Path(cfg["paths"]["raw_frames"]) / "town_probe"
    out.mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        bot.kill.sleep(1.0)
        pts = [c if c == "T" else tuple(int(v) for v in c.split(",")) for c in args.clicks.split()]
        for i, p in enumerate([None] + pts):
            if p == "T":  # automap on/off
                bot.press("tab")
                bot.kill.sleep(0.6)
            elif p is not None:
                bot.click(*p)
                bot.kill.sleep(args.wait)
            f = bot.capture.grab()
            hsv = cv2.cvtColor(f[40:560, 0:1280], cv2.COLOR_BGR2HSV)
            blue = int(((hsv[..., 0] > 95) & (hsv[..., 0] < 130) & (hsv[..., 1] > 110) & (hsv[..., 2] > 140)).sum())
            print(f"{i:02d} {p} blue {blue}", flush=True)  # waypoint flames are bright blue
            cv2.imwrite(str(out / f"{i:02d}.png"), f)
            cv2.imwrite(str(out / f"{i:02d}.jpg"), cv2.resize(f, (640, 360)))
        print(f"{len(pts) + 1} frames in {out}", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
