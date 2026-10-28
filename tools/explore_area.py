"""Explore a waypoint area by teleport (grid frontier, learn.Explorer) over several games and keep a
quarter-size thumbnail of every stop, named by its world position (odometry from the WP arrival view).
Used to find the Durance of Hate Level 3 entrance on Blizzaga's fixed map.

  python tools/explore_area.py wp_durance_2 durance2 --games 3 --hops 40

State resumes from maps/<route>/<name>/explore.json; thumbnails go to maps/<route>/<name>/thumbs/.
Every game ends with save & exit.
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
from bot.learn import Explorer, explore  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.nav import Odometer  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import act4_to, recover_corpse, spawn_act, town_to_wp  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("name")
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--hops", type=int, default=40)
    args = ap.parse_args()

    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    mdir = ROOT / "maps" / cfg["game"]["route"] / args.name
    thumbs = mdir / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    ex_path = mdir / "explore.json"
    ex = Explorer.load(ex_path)

    def keep(frame, pos) -> None:
        cv2.imwrite(str(thumbs / f"{int(pos[0])}_{int(pos[1])}.jpg"),
                    cv2.resize(frame[:590], None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA))

    try:
        for g in range(args.games):
            result = "error"
            try:
                ensure_main_menu(bot)
                create_game(bot, cfg["game"]["difficulty"])
                bot.wait_for("in_game", 10)
                recover_corpse(bot)
                if spawn_act(bot) == 4:
                    act4_to(bot, args.dest, area=None)
                else:
                    town_to_wp(bot, args.dest, None)
                bot.sleep(2.0)  # the "Entering <area>" banner fades (it fools odometry)
                arrival = bot.capture.grab()
                if not (mdir / "arrival.png").exists():
                    cv2.imwrite(str(mdir / "arrival.png"), arrival)
                odo = Odometer(arrival, dungeon=True)
                bot.deadline = bot.clock() + 240
                result = explore(bot, odo, ex, max_hops=args.hops, on_frame=keep, find_bonfires=False)
            except BotError as e:
                print(f"game {g + 1}: {e}", flush=True)
            finally:
                bot.deadline = None
                ex.save(ex_path)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            print(f"game {g + 1}: {result}; {len(ex.visited)} cells, frontier {len(ex.frontier())}", flush=True)
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
