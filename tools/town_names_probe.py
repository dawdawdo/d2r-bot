"""Capture town area names from the automap info (top right) for act detection.

  python tools/town_names_probe.py

New Hell game (spawn wherever the last game ended) -> automap on -> scratch/towns/spawn_<n>.png (full frame) -> waypoint
to the Act III town and the Act I town, a frame with the automap on in each -> save & exit. The area name crops
(durance.AREA_REGION) become templates area_town_a1.png / area_town_a3.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import open_a1_wp, open_a4_wp, open_town_wp, spawn_act, walk_chain, walk_route, wp_travel  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    out = ROOT / "scratch" / "towns"
    out.mkdir(parents=True, exist_ok=True)
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()

    def shot(name: str) -> None:
        bot.press("tab")
        bot.kill.sleep(0.6)
        cv2.imwrite(str(out / f"{name}.png"), bot.capture.grab())
        bot.press("tab")
        bot.kill.sleep(0.3)

    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        bot.kill.sleep(1.0)
        act = spawn_act(bot)
        print(f"spawn_act says {act}", flush=True)
        shot(f"spawn_act{act}")
        if act == 1:
            open_a1_wp(bot)
            wp_travel(bot, "wp_tab_act3", "wp_town")
            bot.kill.sleep(1.5)
            shot("a3_town")
        elif act == 4:
            open_a4_wp(bot)
            wp_travel(bot, "wp_tab_act1", "wp_town")
            bot.kill.sleep(1.5)
            shot("a1_town")
        else:
            tcfg = cfg["town"]
            gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
            if gave_up is not None:
                walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
            open_town_wp(bot, tcfg)
            wp_travel(bot, "wp_tab_act1", "wp_town")
            bot.kill.sleep(1.5)
            shot("a1_town")
        print(f"frames in {out}", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
