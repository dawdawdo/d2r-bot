"""Find the Durance of Hate Level 3 stairs from the Level 2 waypoint, by the bot alone (bot/durance.py).

  python tools/find_durance.py --games 5 --hops 60

Each game: new Hell game -> waypoint Durance 2 -> automap on -> grow the stop graph toward unexplored
automap, hover-scan every new stop for long tooltips (level exits) -> take an untested exit, record
where it leads -> save & exit. Everything resumes from maps/<route>/durance2_auto/ (automap.png,
graph.json, warps/, thumbs/). Run it again after a map change with --fresh.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import STAIRS, AutomapOdometer, StopGraph, Walker, ensure_automap, explore_game, to_durance2  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--hops", type=int, default=60)
    ap.add_argument("--from-stairs", action="store_true",
                    help="travel to the recorded stairs stand spot first, explore from there")
    ap.add_argument("--fresh", action="store_true", help="forget the stored search (map changed)")
    args = ap.parse_args()

    s = start_session()  # backs up saves
    cfg = s.cfg
    folder = ROOT / "maps" / cfg["game"]["route"] / "durance2_auto"
    if args.fresh and folder.exists():
        shutil.move(str(folder), str(folder.with_name(folder.name + "_old")))
    (folder / "thumbs").mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    g = StopGraph.load(folder / "graph.json")
    try:
        for n in range(args.games):
            result = "error"
            odo = None
            try:
                to_durance2(bot, say=lambda m: print(f"game {n + 1}: {m}", flush=True))
                bot.sleep(2.0)  # the "Entering ..." banner fades
                odo = AutomapOdometer.load(folder, ensure_automap(bot))
                print(f"game {n + 1}: arrival fix {odo.pos.round().tolist()} (resp {odo.resp:.2f})", flush=True)

                def save(odo=odo) -> None:
                    odo.save(folder)
                    g.save(folder / "graph.json")

                bot.deadline = bot.clock() + 300
                if args.from_stairs:
                    goal = g.nearest(STAIRS["stand"], within=400)
                    if goal is not None:
                        Walker(bot, odo, g, folder, scan=False).travel(goal)
                    print(f"game {n + 1}: at {odo.pos.round().tolist()}, exploring from here", flush=True)
                result = explore_game(bot, odo, g, folder, max_hops=args.hops, save=save)
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                bot.deadline = None
                if odo is not None:
                    odo.save(folder)
                g.save(folder / "graph.json")
                bot.guard(False)  # a chicken must not fire again while we look and leave
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            warps = [(i, w["w"], w["dest"], w.get("level3")) for i, w in enumerate(g.warps)]
            print(f"game {n + 1}: {result}; {len(g.stops)} stops; warps {warps}", flush=True)
            if any(w.get("level3") for w in g.warps):
                print("Level 3 found", flush=True)
                break
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
