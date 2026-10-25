"""Grab one frame (game client area, or the whole desktop if the game window is missing).

  python tools/peek.py -o shot.png [--scale 0.5] [--wait 60] [--desktop] [--save-raw label]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.io import open_backend, open_desktop_capture, window_info  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--wait", type=float, default=0, help="seconds to wait for the game window")
    ap.add_argument("--desktop", action="store_true")
    ap.add_argument("--save-raw", metavar="LABEL", help="also save full-res frame to fixtures/raw/")
    args = ap.parse_args()

    cfg = load_config()
    title = cfg["game"]["window_title"]
    deadline = time.monotonic() + args.wait
    info = window_info(title)
    while info is None and time.monotonic() < deadline:
        time.sleep(1)
        info = window_info(title)
    print("window:", info)
    if info is None or args.desktop:
        cap = open_desktop_capture()
    else:
        cap = open_backend(title).capture
    frame = cap.grab()
    cap.close()
    if args.save_raw:
        raw = Path(cfg["paths"]["raw_frames"])
        raw.mkdir(parents=True, exist_ok=True)
        p = raw / f"{args.save_raw}_{time.strftime('%Y%m%d-%H%M%S')}.png"
        cv2.imwrite(str(p), frame)
        print("raw:", p)
    small = cv2.resize(frame, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_AREA)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.out, small)
    print(f"frame {frame.shape[1]}x{frame.shape[0]} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
