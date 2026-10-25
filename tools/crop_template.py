"""Crop a template from a frame into bot/assets/templates/.

  python tools/crop_template.py fixtures/labeled/town/x.png 560,20,160,30 town_banner.png

Prints a config snippet for vision.states with a search region padded around the crop.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "bot" / "assets" / "templates"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("rect", help="x,y,w,h")
    ap.add_argument("name")
    ap.add_argument("--pad", type=int, default=20)
    args = ap.parse_args()

    img = cv2.imread(args.frame)
    x, y, w, h = map(int, args.rect.split(","))
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(TEMPLATES / args.name), img[y : y + h, x : x + w])
    p = args.pad
    rx, ry = max(0, x - p), max(0, y - p)
    rw, rh = min(img.shape[1] - rx, w + 2 * p), min(img.shape[0] - ry, h + 2 * p)
    print(f"saved {args.name} ({w}x{h})")
    print(f"- {{template: {args.name}, region: [{rx}, {ry}, {rw}, {rh}], threshold: 0.85}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
