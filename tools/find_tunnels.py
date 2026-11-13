"""Find the Ancient Tunnels entrance in the Lost City, by the bot alone (the Durance stairs finder,
bot/durance.py, with the red automap style and Lost City area checks).

  python tools/find_tunnels.py --games 5 --hops 60 [--fresh]

Each game: new Hell game -> waypoint Lost City -> automap on -> grow the stop graph toward unexplored
automap, hover-scan new stops for long tooltips ("Ancient Tunnels" over the trapdoor) -> take an untested
one, record where it leads -> ALWAYS save & exit. Resumes from maps/<route>/lost_city_auto/.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import (SCAN, AutomapOdometer, StopGraph, area_is, ensure_automap, explore_game,  # noqa: E402
                         to_durance2, use_style)
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def in_lost_city(bot) -> bool:
    return area_is(ensure_automap(bot), "lost_city")


# 2026-11-13 game 1: a poison pack took her 100 -> 18 % in ~4 s during a 25 s scan at the 3rd stop. Now:
# a coarse grid (~6 s), abort on the first few points lost, and no scan at all with monsters moving in view
# or below 85 % life (teleporting on is what keeps her alive; the stop gets scanned on a later visit).
SCAN.update(dx=120, dy=80, abort_hp=4, abort_mp=8, min_w=110, every=3)
QUIET_HP = 85


def safe_to_scan(bot) -> bool:
    from bot.nav import movers

    bot.check()
    if (bot.hp or 100) < QUIET_HP:
        print(f"  no scan: HP {bot.hp:.0f}%", flush=True)
        return False
    m = movers(bot, min_area=400)
    if m:
        print(f"  no scan: {len(m)} moving (largest {m[0][2]} px at {m[0][:2]})", flush=True)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--hops", type=int, default=60)
    ap.add_argument("--fresh", action="store_true", help="forget the stored search (map changed)")
    args = ap.parse_args()

    use_style("red")
    s = start_session()  # backs up saves
    cfg = s.cfg
    folder = ROOT / "maps" / cfg["game"]["route"] / "lost_city_auto"
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
                to_durance2(bot, say=lambda m: print(f"game {n + 1}: {m}", flush=True), dest="wp_lost_city")
                bot.sleep(2.0)
                odo = AutomapOdometer.load(folder, ensure_automap(bot))
                print(f"game {n + 1}: arrival fix {odo.pos.round().tolist()} (resp {odo.resp:.2f})", flush=True)

                def save(odo=odo) -> None:
                    odo.save(folder)
                    g.save(folder / "graph.json")

                bot.deadline = bot.clock() + 300
                result = explore_game(bot, odo, g, folder, max_hops=args.hops, save=save,
                                      here=in_lost_city, goal="ancient_tunnels",
                                      pre_scan=lambda: safe_to_scan(bot))
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                bot.deadline = None
                if odo is not None:
                    odo.save(folder)
                g.save(folder / "graph.json")
                bot.guard(False)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            warps = [(i, w["w"], w["dest"]) for i, w in enumerate(g.warps)]
            print(f"game {n + 1}: {result}; {len(g.stops)} stops; warps {warps}", flush=True)
            if any(w.get("dest") not in (None, "none") for w in g.warps):
                print("an exit was taken: check warps/dest_*.png (Ancient Tunnels?)", flush=True)
                break
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
