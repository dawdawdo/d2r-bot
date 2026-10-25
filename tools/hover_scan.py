"""Find interactable things by hovering a grid and looking for local highlight/tooltip changes.

  python tools/hover_scan.py [--step 40] [--top 10] [--region x,y,w,h]

No clicks are sent. Prints the grid points with the biggest local change versus the
un-hovered frame and saves an annotated frame to scratch/hover_scan.png.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.io import GuardedInput, open_backend  # noqa: E402
from bot.killswitch import KillSwitch  # noqa: E402

PARK = (1270, 590)  # cursor parking spot (right edge, above HUD)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=40)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--region", default="20,40,1240,540")
    ap.add_argument("--settle", type=float, default=0.18)
    args = ap.parse_args()

    cfg = load_config()
    b = open_backend(cfg["game"]["window_title"])
    kill = KillSwitch()
    b.hotkeys.start(cfg["hotkeys"]["kill_switch"], lambda: kill.trip("F12"))
    inp = GuardedInput(b.input, kill)
    b.window.focus()
    time.sleep(0.3)
    rx, ry, rw, rh = map(int, args.region.split(","))
    results = []
    try:
        for y in range(ry, ry + rh, args.step):
            for x in range(rx, rx + rw, args.step):
                inp.move(*PARK)
                kill.sleep(args.settle)
                base = b.capture.grab().astype(np.int16)
                inp.move(x, y)
                kill.sleep(args.settle)
                f = b.capture.grab()
                d = np.abs(f.astype(np.int16) - base).max(axis=2)
                d[max(0, y - 24) : y + 24, max(0, x - 24) : x + 24] = 0  # ignore the cursor itself
                y0, x0 = max(0, y - 120), max(0, x - 120)
                local = d[y0 : y + 120, x0 : x + 120]
                score = float((local > 40).mean() * 100)
                results.append((score, x, y))
    finally:
        inp.move(*PARK)
        b.hotkeys.stop()
    results.sort(reverse=True)
    frame = b.capture.grab()
    for s, x, y in results[: args.top]:
        print(f"({x},{y}) score={s:.2f}")
        cv2.circle(frame, (x, y), 10, (0, 255, 255), 2)
        cv2.putText(frame, f"{s:.1f}", (x + 12, y), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 255), 1)
    out = Path("scratch")
    out.mkdir(exist_ok=True)
    cv2.imwrite(str(out / "hover_scan.png"), cv2.resize(frame, None, fx=0.5, fy=0.5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
