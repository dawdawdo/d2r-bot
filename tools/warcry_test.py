"""Check Call to Arms live: new game -> Lower Kurast -> war cries step by step, saving a crop of the life/mana text
and the buff icons after each step and every 15 s until BO runs out -> save & exit (never left idle out of town).

  python tools/warcry_test.py --out scratch/warcry [--watch 110]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.tasks.lk import LowerKurast  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="scratch/warcry")
    ap.add_argument("--watch", type=float, default=0, help="stay this long watching life/mana, potions and chicken on")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    s = start_session(backup=True)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    b.window.set_client_size(*cfg["game"]["resolution"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    hk = cfg["hotkeys"]
    rows = []

    def snap(label: str) -> None:
        f = b.capture.grab()
        bot.observe()
        life = f[575:600, 240:400]
        mana = f[575:600, 880:1060]
        icons = f[0:60, 80:560]
        pad = np.zeros((25, 480 - 340, 3), np.uint8)
        rows.append(np.vstack([np.hstack([life, mana, pad]), icons]))
        print(f"{time.strftime('%H:%M:%S')} {label}: HP {bot.hp} MP {bot.mp}", flush=True)

    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        bot.act = 3
        LowerKurast(cfg).enter(bot)
        bot.guard(True)
        snap("arrived")
        bot.press(hk["swap_weapons"])
        bot.sleep(0.25)
        snap("swapped")
        for name in hk["warcries"]:
            bot.press(hk["skills"][name])
            bot.sleep(0.1)
            bot.click(*cfg["town"]["corpse_click"], "right", hover=0)
            bot.sleep(0.6)
            snap(name)
        bot.press(hk["swap_weapons"])
        bot.sleep(0.25)
        bot.press(hk["skills"]["teleport"])
        bot.sleep(0.1)
        snap("swapped back")
        t0 = time.time()
        while time.time() - t0 < args.watch:
            bot.sleep(15)
            snap(f"+{time.time() - t0:.0f}s")
    finally:
        try:
            save_and_exit(bot)
        finally:
            bot.release_all()
            s.close()
        if rows:
            cv2.imwrite(str(out / "steps.png"), np.vstack(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
