"""Waypoint Blizzaga to another act's town, save & exit, and capture that act's spawn view.

  python tools/visit_act.py --act 2      # Lut Gholein
  python tools/visit_act.py --act 5      # Harrogath

New Hell game (spawn in Act 3, or Act 1/4 handled) -> A3 town walk -> waypoint -> act tab -> town ->
save & exit -> new game -> fixtures/raw/a<N>_spawn_view.png (+ 2 more a second apart) -> save & exit.
For building the A2/A5 spawn detection (Stephen, 2026-11-02).
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
from bot.town import (leave_act1, open_town_wp, restart_in_act3, spawn_act, wait_arrival,  # noqa: E402
                      walk_chain, walk_route)
from bot.vision.screen import ScreenClassifier  # noqa: E402

TAB_X = {1: 88, 2: 156, 3: 224, 4: 292, 5: 360}  # waypoint panel act tabs (68 px apart, y 90)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", type=int, required=True, choices=[2, 5])
    args = ap.parse_args()
    s = start_session()  # backs up saves
    cfg = s.cfg
    raw = Path(cfg["paths"]["raw_frames"])
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        act = spawn_act(bot)
        if act == 1:
            leave_act1(bot)
        elif act == 4:
            restart_in_act3(bot)
        tcfg = cfg["town"]
        gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
        if gave_up is not None:
            walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
        open_town_wp(bot, tcfg)
        bot.click(TAB_X[args.act], 90)
        bot.kill.sleep(0.4)
        cv2.imwrite(str(raw / f"wp_tab_act{args.act}.png"), bot.capture.grab())
        view = bot.capture.grab()
        bot.click_ui("wp_town")
        wait_arrival(bot, view)
        bot.kill.sleep(1.0)
        cv2.imwrite(str(raw / f"a{args.act}_arrival.png"), bot.capture.grab())
        save_and_exit(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        for k in range(3):
            bot.kill.sleep(1.0)
            cv2.imwrite(str(raw / f"a{args.act}_spawn_view{'' if k == 0 else k}.png"), bot.capture.grab())
        print(f"spawn act guess now: {spawn_act(bot)}; frames in {raw}", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
