"""Teleport along a pattern and stitch the views into one overview map (M4 scouting).

  python tools/explore.py --hops "E*6,N*4,W*6" [--hop 260] [--scale 0.25] [--name lk_scout]

Directions are screen directions (N = up, E = right, NE...). Position is tracked by phase
correlation between consecutive frames (the world scrolls opposite to our movement), which
also catches failed or short teleports. Writes scratch/<name>.png (stitched map, the start
marked green, the path red) and scratch/<name>.json (per-hop commanded vs measured shift).
Safety: F12, user-mouse guard, and save & exit if HP < 50%.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.orbs import orb_pcts  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
        "NE": (0.8, -0.6), "NW": (-0.8, -0.6), "SE": (0.8, 0.6), "SW": (-0.8, 0.6)}
CENTER = (640, 330)  # character's screen position (above the HUD-adjusted center)
VIEW_H = 590         # world area above the HUD


def parse_hops(spec: str) -> list[tuple[int, str]]:
    """'E*3,N*2' -> [(0,'E'),(0,'E'),(0,'E'),(1,'N'),(1,'N')] (leg index, direction)."""
    out = []
    for leg, part in enumerate(spec.split(",")):
        d, _, n = part.strip().partition("*")
        out += [(leg, d.upper())] * int(n or 1)
    return out


def gray_small(frame: np.ndarray, s: float) -> np.ndarray:
    g = cv2.cvtColor(frame[:VIEW_H], cv2.COLOR_BGR2GRAY)
    return cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA).astype(np.float32)


def measure_shift(a: np.ndarray, b: np.ndarray, s: float) -> tuple[float, float, float]:
    """World-scroll from frame a to b, in full-res pixels, plus the response (confidence)."""
    win = cv2.createHanningWindow(a.shape[::-1], cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(a, b, win)
    return dx / s, dy / s, resp


def find_fires(frame: np.ndarray, min_area: int = 120) -> list[tuple[int, int, int]]:
    """Bright saturated orange/yellow blobs (bonfires, torches): (x, y, area) in frame coords."""
    hsv = cv2.cvtColor(frame[:VIEW_H], cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (5, 120, 200), (35, 255, 255))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    return [(int(cen[i][0]), int(cen[i][1]), int(st[i][4])) for i in range(1, n) if st[i][4] >= min_area]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hops", required=True)
    ap.add_argument("--hop", type=int, default=260, help="teleport click distance from center (px)")
    ap.add_argument("--scale", type=float, default=0.25, help="stitched map scale")
    ap.add_argument("--name", default="lk_scout")
    ap.add_argument("--settle", type=float, default=0.45)
    ap.add_argument("--stay", action="store_true",
                    help="don't save & exit at the end (DANGEROUS: idle characters die in Hell)")
    args = ap.parse_args()

    s = start_session(backup=False)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    sc = args.scale
    big = 12000
    canvas = np.zeros((int(big * sc), int(big * sc), 3), np.uint8)
    origin = np.array([big / 2, big / 2])  # full-res world coords of the start view's top-left
    pos = np.array([0.0, 0.0])              # cumulative movement (full-res px) of the camera
    path, log, fires = [], [], []
    lut = np.array([min(255, int(255 * (i / 255) ** 0.5)) for i in range(256)], np.uint8)  # brighten

    def paste(frame):
        x0, y0 = ((origin + pos) * sc).astype(int)
        small = cv2.resize(frame[:VIEW_H], None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        small = cv2.LUT(small, lut)
        h, w = small.shape[:2]
        if 0 <= x0 and 0 <= y0 and y0 + h <= canvas.shape[0] and x0 + w <= canvas.shape[1]:
            canvas[y0 : y0 + h, x0 : x0 + w] = small
        path.append(((origin + pos + CENTER) * sc).astype(int))
        for fx, fy, area in find_fires(frame):
            fires.append({"world": [round(pos[0] + fx - CENTER[0]), round(pos[1] + fy - CENTER[1])],
                          "area": area})

    try:
        bot.release_all()
        frame = b.capture.grab()
        paste(frame)
        prev = gray_small(frame, 0.5)
        stuck = 0
        skip_leg = -1
        potion = 0
        for i, (leg, d) in enumerate(parse_hops(args.hops)):
            if leg == skip_leg:
                continue
            orbs = orb_pcts(frame, cfg["vision"]["orbs"])
            hp, mp = orbs["hp"], orbs["mp"]
            if hp < 45:
                print(f"HP {hp}% -> save & exit")
                save_and_exit(bot)
                break
            if hp < 70:
                key = cfg["hotkeys"]["potions"][potion % 4]
                print(f"HP {hp}% -> potion {key}")
                bot.press(key)
                potion += 1
            if stuck >= 1:
                print(f"stuck -> skipping rest of leg {leg} ({d})")
                stuck = 0
                skip_leg = leg
                continue
            ux, uy = DIRS[d]
            tx, ty = int(CENTER[0] + ux * args.hop), int(CENTER[1] + uy * args.hop * 0.75)
            bot.click(tx, ty, "right")
            s.kill.sleep(args.settle)
            frame = b.capture.grab()
            cur = gray_small(frame, 0.5)
            dx, dy, resp = measure_shift(prev, cur, 0.5)
            # world scrolls by -movement
            pos += np.array([-dx, -dy])
            stuck = stuck + 1 if abs(dx) + abs(dy) < 30 else 0
            log.append({"i": i, "dir": d, "cmd": [tx - CENTER[0], ty - CENTER[1]],
                        "moved": [round(-dx, 1), round(-dy, 1)], "pos": [round(pos[0]), round(pos[1])],
                        "resp": round(resp, 3), "hp": hp, "mp": mp})
            print(f"{i:3d} {d:2s} cmd=({tx - CENTER[0]:+4d},{ty - CENTER[1]:+4d}) "
                  f"moved=({-dx:+7.1f},{-dy:+7.1f}) pos=({pos[0]:+6.0f},{pos[1]:+6.0f}) "
                  f"resp={resp:.2f} hp={hp} mp={mp}")
            paste(frame)
            prev = cur
    finally:
        bot.release_all()
        if not args.stay and not s.kill.tripped:
            try:
                if bot.observe() == "in_game":
                    save_and_exit(bot)
            except Exception as e:  # noqa: BLE001
                print("save & exit at end failed:", e)
        s.close()
        if path:
            for p, q in zip(path, path[1:]):
                cv2.line(canvas, tuple(map(int, p)), tuple(map(int, q)), (0, 0, 255), 1)
            cv2.circle(canvas, tuple(map(int, path[0])), 6, (0, 255, 0), 2)
            for f in fires:
                if f["area"] >= 400:  # bonfire-sized (torches are smaller)
                    c = ((origin + CENTER + np.array(f["world"])) * sc).astype(int)
                    cv2.circle(canvas, tuple(map(int, c)), 5, (0, 255, 255), 1)
            ys, xs = np.where(canvas.any(axis=2))
            if len(xs):
                crop = canvas[max(0, ys.min() - 10) : ys.max() + 10, max(0, xs.min() - 10) : xs.max() + 10]
                Path("scratch").mkdir(exist_ok=True)
                cv2.imwrite(f"scratch/{args.name}.png", crop)
                print(f"map -> scratch/{args.name}.png {crop.shape[1]}x{crop.shape[0]}")
            Path(f"scratch/{args.name}.json").write_text(json.dumps({"hops": log, "fires": fires}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
