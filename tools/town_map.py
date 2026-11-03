"""Learn a town's view map (maps/towns/a<act>/) and its waypoint position, by walking it in new games.

  python tools/town_map.py --act 2 --games 4            # explore from each spawn until it joins the map, then walk to the WP
  python tools/town_map.py --act 2 --seed fixtures/raw/town_probe 5 16   # seed from a probe walk (frames 05..16)

Only for an act the saves spawn in (Stephen's game ended there). Never takes the waypoint (that would move the
spawn to Act 3): each game ends with save & exit.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import A2_WALK, A2_WP_CLICK, A5_WALK, A5_WP_CLICK, spawn_act  # noqa: E402
from bot.townnav import Walker, open_by_map  # noqa: E402
from bot.vision.screen import ASSETS, ScreenClassifier, match_score  # noqa: E402
from bot.vision.viewmap import MIN_VOTES, ViewMap, features, offset  # noqa: E402

log = logging.getLogger("town_map")
WP = {2: ("a2_wp.png", A2_WP_CLICK), 5: ("a5_wp.png", A5_WP_CLICK)}


def wp_on_screen(frame, act: int) -> tuple[int, int] | None:
    tpl, off = WP[act]
    s, loc = match_score(frame, cv2.imread(str(ASSETS / tpl)), (0, 0, 1280, 600))
    return (loc[0] + off[0], loc[1] + off[1]) if s >= 0.8 else None


def seed(vmap: ViewMap, folder: Path, a: int, b: int, act: int) -> None:
    pos = (0.0, 0.0)
    prev = None
    for i in range(a, b + 1):
        fr = cv2.imread(str(folder / f"{i:02d}.png"))
        f = features(fr)
        if prev is not None:
            (dx, dy), n = offset(prev, f)
            if n < MIN_VOTES:
                raise SystemExit(f"frame {i}: no overlap with the previous one ({n} votes)")
            pos = (pos[0] + dx, pos[1] + dy)
        prev = f
        if vmap.nearest(pos) > 150:
            vmap.add(fr, pos)
        wp = wp_on_screen(fr, act)
        if wp and "wp" not in vmap.targets:
            vmap.targets["wp"] = [round(pos[0] + wp[0] - 640, 1), round(pos[1] + wp[1] - 360, 1)]
    vmap.save()
    print(f"seeded {len(vmap.frames)} views, targets {vmap.targets}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", type=int, default=2)
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--seed", nargs=3, metavar=("DIR", "FIRST", "LAST"))
    args = ap.parse_args()
    vmap = ViewMap.load(ROOT / "maps" / "towns" / f"a{args.act}")
    if args.seed:
        seed(vmap, Path(args.seed[0]), int(args.seed[1]), int(args.seed[2]), args.act)
        return 0
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    results = []
    try:
        for g in range(args.games):
            ensure_main_menu(bot)
            create_game(bot, cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
            bot.kill.sleep(1.0)
            act = spawn_act(bot)
            if act != args.act:
                print(f"spawned in act {act}, not {args.act}: stop")
                break
            w = Walker(bot, vmap, learn=True)
            w.start()
            print(f"game {g + 1}: start {'at %s' % (w.pos,) if w.pos else 'off the map'}", flush=True)
            reached = False
            walk = A2_WALK if args.act == 2 else A5_WALK
            for i in range(args.steps):
                fr = bot.capture.grab()
                wp = wp_on_screen(fr, args.act)
                if wp and w.pos is not None and "wp" not in vmap.targets:
                    t = [round(w.pos[0] + wp[0] - 640, 1), round(w.pos[1] + wp[1] - 360, 1)]
                    if "wp" not in vmap.targets:
                        vmap.targets["wp"] = t
                    print(f"  step {i}: waypoint on screen at {wp}; world {t} (map says {vmap.targets['wp']})")
                    reached = True
                    break
                if w.pos is None and i < len(walk):
                    bot.click(*walk[i])  # off the map: the old click walk passes through the mapped streets
                    w._track()
                    w.fix()
                    print(f"  step {i}: walk click {walk[i]} -> {'at (%.0f, %.0f)' % w.pos if w.pos else 'off the map'}", flush=True)
                elif w.pos is None or "wp" not in vmap.targets:
                    w.explore_step()
                    if w.pos is None:
                        w.fix()
                else:
                    d = w.toward(tuple(vmap.targets["wp"]))
                    print(f"  step {i}: at ({w.pos[0]:.0f}, {w.pos[1]:.0f}), wp {d:.0f} px", flush=True)
                    if d < 400 and open_by_map(bot, w, tuple(vmap.targets["wp"])):
                        print(f"  step {i}: waypoint menu opened by the map", flush=True)
                        cv2.imwrite(str(ROOT / "fixtures" / "raw" / f"town_map_wp_{g}.png"), bot.capture.grab())
                        bot.press("esc")
                        bot.kill.sleep(0.5)
                        reached = True
                        break
                    if i % 3 == 2:
                        w.fix()
            vmap.save()
            results.append(reached)
            cv2.imwrite(str(ROOT / "fixtures" / "raw" / f"town_map_end_{g}.png"), bot.capture.grab())
            print(f"game {g + 1}: {'reached' if reached else 'NOT reached'}; map has {len(vmap.frames)} views", flush=True)
            save_and_exit(bot)
    finally:
        vmap.save()
        if bot.observe() not in ("main_menu",):
            try:
                save_and_exit(bot)
            except Exception:  # noqa: BLE001
                pass
        bot.release_all()
        s.close()
    print("results:", results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
