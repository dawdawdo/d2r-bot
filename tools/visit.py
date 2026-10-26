"""Scout huts: from the LK waypoint, teleport to world targets and hover-scan each for tooltips.

  python tools/visit.py --targets "-1300,0 2000,2150" [--name sc_huts] [--bonfire 1629,776]

Run right after tools/goto_lk.py (character on the LK waypoint). Saves a contact sheet per target
(scratch/<name>_<i>.png: view + tooltip crops) and ends with save & exit. With --bonfire, odometry is
re-anchored on that bonfire at each target (if in view), and chest tooltips are printed in world coords.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.lk import _is_chest  # noqa: E402
from bot.nav import Odometer, reanchor, fight, scan_tooltips, teleport_to, CENTER  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True, help='space-separated "x,y" world coords')
    ap.add_argument("--name", default="visit")
    ap.add_argument("--bonfire", help='"x,y" world coords of a bonfire to anchor on')
    args = ap.parse_args()
    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    bot.guard(True)
    try:
        odo = Odometer(b.capture.grab())
        for i, t in enumerate(args.targets.split()):
            tx, ty = map(float, t.split(","))
            ok = teleport_to(bot, odo, (tx, ty))
            fight(bot, max_casts=10, odo=odo)
            odo.update(b.capture.grab())
            if args.bonfire:
                reanchor(bot, odo, tuple(map(float, args.bonfire.split(","))))
                ok = teleport_to(bot, odo, (tx, ty), tol=60)  # reanchor may have moved us to the bonfire
            view = b.capture.grab()
            hits = scan_tooltips(bot)
            chests = []
            for x, y, crop in hits:
                if _is_chest(crop, (0, 0, crop.shape[1], crop.shape[0])):
                    chests.append((round(odo.pos[0] + x - CENTER[0]), round(odo.pos[1] + y - CENTER[1])))
            print(f"target {i} ({tx:.0f},{ty:.0f}) reached={ok} at {odo.pos.round().tolist()} "
                  f"lost={odo.lost} tooltips={[(x, y) for x, y, _ in hits]} chests_world={chests}", flush=True)
            small = cv2.resize(view, None, fx=0.5, fy=0.5)
            crops = [cv2.resize(c, (220, 40)) for _, _, c in hits[:16]] or [np.zeros((40, 220, 3), np.uint8)]
            col = np.vstack(crops)
            h = max(small.shape[0], col.shape[0])
            sheet = np.hstack([cv2.copyMakeBorder(small, 0, h - small.shape[0], 0, 0, cv2.BORDER_CONSTANT),
                               cv2.copyMakeBorder(col, 0, h - col.shape[0], 0, 0, cv2.BORDER_CONSTANT)])
            cv2.imwrite(f"scratch/{args.name}_{i}.png", sheet)
    except BotError as e:
        print("guardian/abort:", e)
    finally:
        bot.release_all()
        bot.guard(False)
        try:
            if bot.observe() == "in_game":
                save_and_exit(bot)
        except Exception as e:  # noqa: BLE001
            print("save & exit failed:", e)
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
