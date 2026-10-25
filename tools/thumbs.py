"""Contact sheet of downscaled frames, for cheap visual review.

  python tools/thumbs.py fixtures/raw/town_*.png -o sheet.png --width 320 --cols 4
  python tools/thumbs.py frame.png --crop 0,560,400,160 --scale 1 -o hud.png

Each tile is captioned with its index and filename so frames can be referred to by number.
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import cv2
import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns", nargs="+")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--width", type=int, default=320, help="tile width (ignored with --scale)")
    ap.add_argument("--scale", type=float, default=0, help="scale factor instead of --width")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--crop", help="x,y,w,h applied before scaling")
    ap.add_argument("--grid", type=int, default=0, help="draw a coordinate grid every N px")
    args = ap.parse_args()

    paths = sorted({p for pat in args.patterns for p in glob.glob(pat)})
    if not paths:
        raise SystemExit("no files")
    tiles = []
    for i, p in enumerate(paths):
        img = cv2.imread(p)
        ox = oy = 0
        if args.crop:
            ox, oy, w, h = map(int, args.crop.split(","))
            img = img[oy : oy + h, ox : ox + w]
        if args.grid:
            img = img.copy()
            for gx in range(-(ox % args.grid) + args.grid, img.shape[1], args.grid):
                cv2.line(img, (gx, 0), (gx, img.shape[0]), (0, 255, 255), 1)
                cv2.putText(img, str(gx + ox), (gx + 2, 12), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 255, 255), 1)
            for gy in range(-(oy % args.grid) + args.grid, img.shape[0], args.grid):
                cv2.line(img, (0, gy), (img.shape[1], gy), (0, 255, 255), 1)
                cv2.putText(img, str(gy + oy), (2, gy - 2), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 255, 255), 1)
        s = args.scale or args.width / img.shape[1]
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        cap = np.zeros((16, img.shape[1], 3), np.uint8)
        cv2.putText(cap, f"{i}: {Path(p).name}"[:60], (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.9, (255, 255, 255), 1)
        tiles.append(np.vstack([cap, img]))
    th = max(t.shape[0] for t in tiles)
    tw = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, th - t.shape[0], 0, tw - t.shape[1], cv2.BORDER_CONSTANT) for t in tiles]
    while len(tiles) % args.cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[r : r + args.cols]) for r in range(0, len(tiles), args.cols)]
    cv2.imwrite(args.out, np.vstack(rows))
    for i, p in enumerate(paths):
        print(i, p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
