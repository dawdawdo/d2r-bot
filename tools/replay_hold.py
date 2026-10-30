"""Replay Stephen's second teleport hold from the recorded stand spot, looking for the Level 3 stairs.

  python tools/replay_hold.py --games 1 --hops 16

His recording logged one right-click per hold (the recorder samples presses only). The first hold,
cursor at (1100, 433), carried him ~5800 px east to the stand spot; the second, cursor at (984, 257),
for ~4 s, ended next to the stairs (his left click at (636, 251)). So: from the stand spot, teleport
toward (984, 257) again and after each hop hover around (636, 251) for the exit's long tooltip.
Every hop's view goes to maps/<route>/durance2_route/hold/ for review. A find is saved as stairs.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import (STAIRS, AutomapOdometer, StopGraph, Walker, durance_level, ensure_automap,  # noqa: E402
                         find_stairs, to_durance2)
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.nav import CENTER, hop  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

HOLD_CURSOR = (984, 257)
CLICK = STAIRS["click"]


def replay(bot, odo, folder: Path, hops: int, say) -> bool:
    out = folder / "hold"
    out.mkdir(parents=True, exist_ok=True)
    dx, dy = HOLD_CURSOR[0] - CENTER[0], HOLD_CURSOR[1] - CENTER[1]
    for i in range(hops):
        hop(bot, odo, dx, dy)
        f = bot.capture.grab()
        cv2.imwrite(str(out / f"{i:02d}.jpg"), cv2.resize(f, (640, 360)), [cv2.IMWRITE_JPEG_QUALITY, 85])
        say(f"hop {i}: {odo.pos.round().tolist()} resp {odo.resp:.2f}{' LOST' if odo.lost else ''}")
        hit = find_stairs(bot, CLICK, radius=130, step=40, folder=out)
        if hit is None:
            # the exit's label may not look like an object tooltip: keep a hover frame, click anyway
            bot.input.move(*CLICK)
            bot.kill.sleep(0.15)
            cv2.imwrite(str(out / f"{i:02d}_hover.png"), bot.capture.grab())
            bot.click(*CLICK)
            bot.sleep(2.5)
            if durance_level(ensure_automap(bot)) == 3:
                world = [float(odo.pos[0] + CLICK[0] - 640), float(odo.pos[1] + CLICK[1] - 330)]
                (folder / "stairs.json").write_text(json.dumps({"world": world, "hops": i + 1, "blind": True}))
                say(f"Level 3 by a blind click! stairs world {[round(v) for v in world]}")
                return True
            continue
        (x, y), crop = hit
        world = [float(odo.pos[0] + x - 640), float(odo.pos[1] + y - 330)]
        cv2.imwrite(str(out / "tooltip.png"), crop)
        say(f"long tooltip hovering ({x}, {y}) at hop {i}; clicking")
        bot.click(x, y)
        bot.sleep(2.5)
        if durance_level(ensure_automap(bot)) == 3:
            (folder / "stairs.json").write_text(json.dumps({"world": world, "hops": i + 1, "lost": bool(odo.lost)}))
            say(f"Level 3! stairs world {[round(v) for v in world]}")
            return True
        say("clicked, but not on Level 3")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1)
    ap.add_argument("--hops", type=int, default=16)
    args = ap.parse_args()

    s = start_session()  # backs up saves
    cfg = s.cfg
    maps = ROOT / "maps" / cfg["game"]["route"]
    auto = maps / "durance2_auto"
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    g = StopGraph.load(auto / "graph.json")
    found = False
    try:
        for n in range(args.games):
            say = lambda m, n=n: print(f"game {n + 1}: {m}", flush=True)  # noqa: E731
            t0 = time.time()
            try:
                to_durance2(bot, say=say)
                bot.sleep(2.0)
                odo = AutomapOdometer.load(auto, ensure_automap(bot))
                walker = Walker(bot, odo, g, auto, scan=False)
                goal = g.nearest(STAIRS["stand"], within=400)
                if goal is not None:
                    walker.travel(goal)
                walker.go(STAIRS["stand"], tol=120, max_hops=8)
                say(f"at the stand spot {odo.pos.round().tolist()}")
                found = replay(bot, odo, maps / "durance2_route", args.hops, say)
            except BotError as e:
                say(str(e))
            finally:
                bot.guard(False)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            say(f"{time.time() - t0:.0f}s total")
            if found:
                break
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
