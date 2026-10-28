"""Stitch exploration thumbnails (maps/<route>/<name>/thumbs/<x>_<y>.jpg, quarter size, named by world
position) into one map image. Later thumbs paint over earlier ones; a red dot marks each stop.

  python tools/mosaic.py maps/blizzaga_hell/durance2 out.png [--scale 0.5]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=1.0, help="extra downscale of the result")
    args = ap.parse_args()
    items = []
    for p in sorted(Path(args.dir, "thumbs").glob("*.jpg"), key=lambda p: p.stat().st_mtime):
        x, y = map(int, p.stem.split("_"))
        items.append((x / 4, y / 4, cv2.imread(str(p))))
    h, w = items[0][2].shape[:2]
    xs, ys = [i[0] for i in items], [i[1] for i in items]
    ox, oy = -min(xs) + w / 2, -min(ys) + h / 2
    W, H = int(max(xs) - min(xs) + w), int(max(ys) - min(ys) + h)
    canvas = np.zeros((H, W, 3), np.uint8)
    for x, y, img in items:
        x0, y0 = int(x + ox - w / 2), int(y + oy - h / 2)
        canvas[y0 : y0 + h, x0 : x0 + w] = np.maximum(canvas[y0 : y0 + h, x0 : x0 + w], img)
    for x, y, _ in items:
        cv2.circle(canvas, (int(x + ox), int(y + oy)), 3, (0, 0, 255), -1)
    cv2.circle(canvas, (int(ox), int(oy)), 6, (0, 255, 0), 2)  # the waypoint (world 0, 0)
    if args.scale != 1.0:
        canvas = cv2.resize(canvas, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_AREA)
    cv2.imwrite(args.out, canvas)
    print(f"{len(items)} thumbs -> {canvas.shape[1]}x{canvas.shape[0]}, waypoint at {int(ox)},{int(oy)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
