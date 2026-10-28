"""Scout an area (dev helper): new Hell game -> waypoint `dest` -> steps -> ALWAYS save & exit.

  python tools/scout.py wp_durance_2 shot:arrive map:arrive tp:300:-150 shot:a1 tp:300:-150 map:a2

Steps (':' separated, PowerShell eats commas):
  tp:dx:dy     teleport by a screen offset from the character (odometry tracked, printed)
  shot:label   save the view to fixtures/raw/scout_<label>_<time>.png (+ a half-size copy in --out)
  map:label    same, with the automap open (Tab), then close it
  hover:x:y    move the mouse there and save a shot (tooltips)
  wait:s
Guarded: chicken/HP checks run (bot.guard on), F12 stops. Prints odometry after every hop.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.nav import Odometer, hop  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import act4_to, recover_corpse, spawn_act, town_to_wp  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest", help="ui point on the waypoint's Act III tab, e.g. wp_durance_2")
    ap.add_argument("steps", nargs="*")
    ap.add_argument("--out", help="folder for half-size copies (to look at)")
    args = ap.parse_args()

    s = start_session()  # backs up saves
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    raw = Path(cfg["paths"]["raw_frames"])
    raw.mkdir(parents=True, exist_ok=True)

    def save(label: str, frame) -> None:
        name = f"scout_{label}_{time.strftime('%H%M%S')}.png"
        cv2.imwrite(str(raw / name), frame)
        if args.out:
            cv2.imwrite(str(Path(args.out) / f"{label}.png"),
                        cv2.resize(frame, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
        print("saved", name, flush=True)

    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        recover_corpse(bot)
        if spawn_act(bot) == 4:
            act4_to(bot, args.dest, area=None)
        else:
            town_to_wp(bot, args.dest, None)
        odo = Odometer(bot.capture.grab(), dungeon=True)
        for step in args.steps:
            kind, _, rest = step.partition(":")
            if kind == "tp":
                dx, dy = map(int, rest.split(":"))
                hop(bot, odo, dx, dy)
                print("odo", odo.pos.round().tolist(), "lost" if odo.lost else "", flush=True)
            elif kind == "shot":
                bot.wait_still(timeout=2)
                save(rest, bot.capture.grab())
            elif kind == "map":
                bot.press("tab")
                bot.kill.sleep(0.4)
                save(rest, bot.capture.grab())
                bot.press("tab")
                bot.kill.sleep(0.3)
            elif kind == "hover":
                x, y = map(int, rest.split(":"))
                bot.input.move(x, y)
                bot.kill.sleep(0.4)
                save(f"hover_{x}_{y}", bot.capture.grab())
            elif kind == "wait":
                bot.sleep(float(rest))
            else:
                raise SystemExit(f"bad step {step}")
    finally:
        bot.release_all()
        try:
            if bot.observe() != "main_menu":
                save_and_exit(bot)  # never leave her standing outside town
        finally:
            s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
