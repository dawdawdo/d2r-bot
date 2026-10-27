"""Map hunting (docs/roadmap.md): reroll Blizzaga's Hell map until Lower Kurast has enough super-chest
camps, learn it, and switch the bot to it.

  python tools/hunt_map.py --replaces-current-map [--min-camps 2] [--maps 10] [--games 6]

!! Every reroll REPLACES the character's current Hell map (and the learned route stops matching).
!! Stephen's current map is a good one: run this only when he asks for it.

How a reroll works: entering a game on another difficulty makes D2R regenerate the character's maps
(researched 2026-10-27), so: Normal game -> save & exit -> Hell game = new Hell map. No save files are
touched. Each candidate map is explored for up to `--games` games (bot/learn.py), its bonfire camps
verified by chest tooltips, and scored by verified camps (then route length).
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import learn, state  # noqa: E402
from bot.config import ROOT  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

log = logging.getLogger("hunt_map")


def reroll(bot: Controller) -> None:
    """Normal game, then out: the next Hell game gets a new map."""
    ensure_main_menu(bot)
    create_game(bot, "normal")
    bot.wait_for("in_game", 30)
    save_and_exit(bot)
    log.info("rerolled: entered Normal; the next Hell game has a new map")


def route_length(route: dict) -> float:
    from bot.lk import BONFIRE_LAYOUT

    pts = [(c["world"][0] + BONFIRE_LAYOUT[k]["stand"][0], c["world"][1] + BONFIRE_LAYOUT[k]["stand"][1])
           for c in route["bonfires"] for k in c["order"]]
    return learn._path_len((0.0, 0.0), pts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replaces-current-map", action="store_true", required=True,
                    help="required: each reroll replaces the character's Hell map")
    ap.add_argument("--min-camps", type=int, default=2)
    ap.add_argument("--maps", type=int, default=10, help="give up after this many rerolls")
    ap.add_argument("--games", type=int, default=6, help="exploration games per candidate map")
    ap.add_argument("--hops", type=int, default=70)
    args = ap.parse_args()

    s = start_session()  # backs up the saves first
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    best = None
    try:
        for k in range(args.maps):
            reroll(bot)
            name = f"hunt_{time.strftime('%Y%m%d_%H%M')}_{k + 1}"
            route = learn.learn_map(bot, name, games=args.games, hops=args.hops)
            camps = len(route["bonfires"]) if route else 0
            length = route_length(route) if route else float("inf")
            log.info("map %d (%s): %d verified camps, route %.0f px", k + 1, name, camps, length)
            if route and (best is None or (camps, -length) > (best[1], -best[2])):
                best = (name, camps, length)
            if camps >= args.min_camps:
                state.save({**state.load(), "route": name})
                log.warning("keeping map %s (%d camps); the bot now runs maps/%s (logs/state.json route)",
                            name, camps, name)
                return 0
        log.error("no map with %d+ camps in %d rerolls (best %s); the current map is the last one tried",
                  args.min_camps, args.maps, best)
        if best:
            log.error("note: the best one (%s) is gone too; rerolling can't go back", best[0])
        return 1
    finally:
        bot.release_all()
        b.capture.close()
        s.close()


if __name__ == "__main__":
    raise SystemExit(main())
