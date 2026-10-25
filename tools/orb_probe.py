"""Measure orb liquid extents in a frame to calibrate config vision.orbs.

  python tools/orb_probe.py frame.png [--hp-center 328,657] [--mp-center 988,657]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.vision.color import hsv_mask  # noqa: E402


def probe(frame, name, cx, cy, rng, half=80):
    x0, y0 = cx - half, max(0, cy - half)
    sub = frame[y0 : cy + half, x0 : cx + half]
    m = hsv_mask(sub, rng) > 0
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    print(f"{name}: center HSV {hsv[cy, cx]}  mask frac {m.mean():.2f}")
    col = m[:, half - 10 : half + 10].mean(1) > 0.5
    row = m[cy - y0 - 3 : cy - y0 + 3].mean(0) > 0.5
    if col.any():
        ys = np.where(col)[0] + y0
        print(f"  liquid rows {ys.min()}..{ys.max()} (center column)")
    if row.any():
        xs = np.where(row)[0] + x0
        print(f"  liquid cols {xs.min()}..{xs.max()} (center row)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--hp-center", default="328,657")
    ap.add_argument("--mp-center", default="988,657")
    args = ap.parse_args()
    cfg = load_config()["vision"]["orbs"]
    f = cv2.imread(args.frame)
    for name, c in (("hp", args.hp_center), ("mp", args.mp_center)):
        cx, cy = map(int, c.split(","))
        probe(f, name, cx, cy, cfg[name]["color"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
