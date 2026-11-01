"""Open Ormus's trade window and save frames (for building potion buying).

  python tools/ormus_trade_probe.py [--offset 37,55]

New Hell game (Act 3; an A4 spawn goes back to A3 first) -> walk to Ormus -> click him -> dialog ->
click "Trade" at the offset from the npc_ormus.png match -> frames to fixtures/raw/ormus_*.png ->
Esc, save & exit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.gamesettings import ensure_options  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import _tooltip_points, restart_in_act3, spawn_act, walk_route  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset", default="37,55")
    args = ap.parse_args()
    ox, oy = (int(v) for v in args.offset.split(","))
    s = start_session()
    cfg = s.cfg
    raw = Path(cfg["paths"]["raw_frames"])
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        ensure_options(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        if spawn_act(bot) == 4:
            restart_in_act3(bot)
        tcfg = cfg["town"]
        walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]])
        for attempt, (x, y) in enumerate(_tooltip_points(bot, tcfg["ormus_region"])):
            if attempt >= 5:
                break
            bot.click(x, y)
            bot.kill.sleep(2.0)
            loc = bot.find("npc_ormus.png", region=(0, 0, 1280, 500), threshold=0.8)
            if loc is None:
                bot.press("esc")
                bot.kill.sleep(0.3)
                continue
            f = bot.capture.grab()
            cv2.imwrite(str(raw / "ormus_dialog.png"), f)
            print(f"dialog: npc_ormus.png at {loc}", flush=True)
            bot.click(loc[0] + ox, loc[1] + oy)
            bot.kill.sleep(1.5)
            cv2.imwrite(str(raw / "ormus_trade.png"), bot.capture.grab())
            print("saved ormus_trade.png", flush=True)
            bot.press("esc")
            bot.kill.sleep(0.5)
            break
        else:
            print("Ormus not found", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
