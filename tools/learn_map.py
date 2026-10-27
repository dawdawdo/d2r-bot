"""Learn a Lower Kurast map (bot/learn.py): explore from the waypoint over several games, find
bonfire camps, verify their chest spots, plan a route.

  python tools/learn_map.py --name learn_test --games 4 --hops 70   # explore only (resumes explore.json)
  python tools/learn_map.py --name learn_test --verify               # visit each candidate camp, hover chests
  python tools/learn_map.py --name learn_test --plan                 # write maps/<name>/route.yaml
  python tools/learn_map.py --name learn_test --all --games 15       # all three

Every game ends with save & exit (never idle outside town). F12 stops.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import learn  # noqa: E402
from bot.config import ROOT  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--hops", type=int, default=70, help="teleports per game")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    mdir = ROOT / "maps" / args.name
    if args.plan:
        ver = mdir / "verified.json"
        route = learn.write_route(mdir, json.loads(ver.read_text()) if ver.exists() else {})
        print(yaml.safe_dump(route, sort_keys=False) if route else "no verified camps")
        return 0
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    try:
        if args.all:
            print(learn.learn_map(bot, args.name, games=args.games, hops=args.hops))
        elif args.verify:
            print(json.dumps(learn.verify_games(bot, mdir, learn.Explorer.load(mdir / "explore.json")), indent=1))
        else:
            learn.explore_games(bot, mdir, args.games, args.hops)
    finally:
        bot.release_all()
        b.capture.close()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
