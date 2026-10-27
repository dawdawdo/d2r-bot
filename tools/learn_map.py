"""Learn a Lower Kurast map: explore from the waypoint over several games, find bonfire camps,
verify their chest spots, plan a route (bot/learn.py).

  python tools/learn_map.py --name learn_test --games 4 --hops 100     # explore (resumes explore.json)
  python tools/learn_map.py --name learn_test --verify                  # visit each candidate camp, hover chests
  python tools/learn_map.py --name learn_test --plan                    # print/write maps/<name>/route.yaml

Every game ends with save & exit (never idle outside town). F12 stops.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import cv2
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.learn import Explorer, explore, plan_route  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.lk import BONFIRE_LAYOUT, open_chest  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import town_to_lower_kurast  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

log = logging.getLogger("learn_map")
FP_REGION = [520, 290, 240, 140]  # same crop as the hand route's fingerprint


def to_lk(bot: Controller, cfg: dict):
    from bot.nav import Odometer

    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    town_to_lower_kurast(bot)
    return Odometer(bot.capture.grab())


def verify_camp(bot: Controller, odo, bonfire) -> dict:
    """Anchor on the bonfire, then hover each layout chest spot. Returns {slot: found}."""
    from bot.nav import reanchor, teleport_to, world_to_screen

    out = {}
    if not reanchor(bot, odo, bonfire):
        log.warning("verify: no bonfire at %s", bonfire)
        return out
    for slot, lay in BONFIRE_LAYOUT.items():
        stand = (bonfire[0] + lay["stand"][0], bonfire[1] + lay["stand"][1])
        teleport_to(bot, odo, stand)
        bot.wait_still(timeout=1.0, settle=1, poll=0.05, min_wait=0.0)
        odo.update(bot.capture.grab())
        cx, cy = world_to_screen(odo, bonfire[0] + lay["chest"][0], bonfire[1] + lay["chest"][1])
        out[slot] = open_chest(bot, cx, cy, click=False) is not None
        log.info("verify %s %s: %s", bonfire, slot, "chest" if out[slot] else "no chest")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--hops", type=int, default=100, help="teleports per game")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--write", action="store_true", help="with --plan: write maps/<name>/route.yaml")
    args = ap.parse_args()

    mdir = ROOT / "maps" / args.name
    ex_path, ver_path = mdir / "explore.json", mdir / "verified.json"
    ex = Explorer.load(ex_path)
    if args.plan:
        verified = json.loads(ver_path.read_text()) if ver_path.exists() else {}
        camps = [tuple(map(int, k.split(","))) for k, v in verified.items() if sum(v.values()) >= 2]
        if not camps:
            camps = ex.bonfires()
            print("no verified camps; planning from unverified bonfires", camps)
        route = {"fingerprint": {"template": f"lk_wp_{args.name}.png", "region": FP_REGION,
                                 "threshold": 0.6, "half_threshold": 0.5},
                 "bonfires": plan_route(camps, BONFIRE_LAYOUT), "targets": []}
        print(yaml.safe_dump(route, sort_keys=False))
        if args.write:
            (mdir / "route.yaml").write_text(yaml.safe_dump(route, sort_keys=False))
            print("wrote", mdir / "route.yaml")
        return 0

    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    try:
        if args.verify:
            verified = json.loads(ver_path.read_text()) if ver_path.exists() else {}
            for bf in ex.bonfires():
                key = f"{bf[0]},{bf[1]}"
                if key in verified:
                    continue
                try:
                    odo = to_lk(bot, cfg)
                    bot.deadline = bot.clock() + 120
                    verified[key] = verify_camp(bot, odo, bf)
                except BotError as e:
                    log.warning("verify %s: %s", bf, e)
                finally:
                    bot.deadline = None
                    if bot.state != "main_menu":
                        save_and_exit(bot)
                mdir.mkdir(parents=True, exist_ok=True)
                ver_path.write_text(json.dumps(verified, indent=1))
            print(json.dumps(verified, indent=1))
            return 0
        for g in range(args.games):
            result = "error"
            try:
                odo = to_lk(bot, cfg)
                if not (mdir / f"lk_wp_{args.name}.png").exists():
                    x, y, w, h = FP_REGION
                    mdir.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(mdir / f"lk_wp_{args.name}.png"), bot.capture.grab()[y : y + h, x : x + w])
                bot.deadline = bot.clock() + 240
                result = explore(bot, odo, ex, max_hops=args.hops, debug_dir=mdir / "fires")
            except BotError as e:
                log.warning("game %d: %s", g + 1, e)
            finally:
                bot.deadline = None
                if bot.state != "main_menu":
                    save_and_exit(bot)
                ex.save(ex_path)
            log.info("game %d: %s; %d cells visited, %d frontier, fires %s", g + 1, result, len(ex.visited),
                     len(ex.frontier()), [(round(f["x"]), round(f["y"]), f["n"]) for f in ex.fires])
            if result == "done":
                break
    finally:
        bot.release_all()
        b.capture.close()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
