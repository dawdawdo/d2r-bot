"""Open Blizzaga's stash in Act 3 and save a frame of a tab (to measure the stash grid / check items).

  python tools/stash_look.py [--tab personal_tab] [--out stash]

New Hell game -> Act 3 -> town walk -> stash -> click the tab -> scratch/<out>/stash_<tab>.png -> Esc -> save & exit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import (ensure_main_weapons, leave_other_act, open_stash, restart_in_act3, spawn_act,  # noqa: E402
                      walk_chain, walk_route)
from bot.vision.screen import ScreenClassifier  # noqa: E402


def to_stash(bot, cfg) -> None:
    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)
    act = spawn_act(bot)
    if act == 4:
        restart_in_act3(bot)
    elif act != 3:
        leave_other_act(bot, act)
    bot.weapons_dirty = True
    ensure_main_weapons(bot)  # the orb + shield set up: the swap must land on it
    tcfg = cfg["town"]
    gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
    if gave_up is not None:
        walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
    if not open_stash(bot):
        raise BotError("stash didn't open")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tab", default="personal_tab")
    ap.add_argument("--out", default="stash")
    args = ap.parse_args()
    out = ROOT / "scratch" / args.out
    out.mkdir(parents=True, exist_ok=True)
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        to_stash(bot, cfg)
        bot.click_ui(args.tab) if args.tab in cfg["ui"] else bot.click(*cfg["stash"][args.tab])
        bot.kill.sleep(0.6)
        bot.input.move(640, 650)
        bot.kill.sleep(0.3)
        cv2.imwrite(str(out / f"stash_{args.tab}.png"), bot.capture.grab())
        bot.press("esc")
        bot.kill.sleep(0.4)
        print(f"frame in {out}", flush=True)
    except BotError as e:
        print(f"error: {e}", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
