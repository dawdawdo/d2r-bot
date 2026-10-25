"""Hover-scan a region for NPC name tooltips; optionally click the first hit and capture the dialog.

  python tools/npc_probe.py [--region 500,60,500,300] [--click]
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="420,40,560,340")
    ap.add_argument("--step", type=int, default=30)
    ap.add_argument("--click", action="store_true")
    args = ap.parse_args()
    cfg = load_config()
    b = open_backend(cfg["game"]["window_title"])
    kill = KillSwitch()
    b.hotkeys.start("f12", lambda: kill.trip("F12"))
    inp = GuardedInput(b.input, kill)
    b.window.focus()
    time.sleep(0.2)
    rx, ry, rw, rh = map(int, args.region.split(","))
    inp.move(1270, 590)
    time.sleep(0.15)
    base = cv2.cvtColor(b.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
    hit = None
    for y in range(ry, ry + rh, args.step):
        for x in range(rx, rx + rw, args.step):
            inp.move(x, y)
            time.sleep(0.07)
            f = b.capture.grab()
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.int16)
            y0, x0 = max(0, y - 140), max(0, x - 120)
            if (np.abs(g[y0:y, x0 : x + 120] - base[y0:y, x0 : x + 120]) > 60).mean() > 0.02:
                hit = (x, y)
                cv2.imwrite("scratch/npc_hit.png", f[y0 : y + 20, x0 : x + 120])
                break
        if hit:
            break
    print("hit:", hit)
    if hit and args.click:
        inp.click(*hit)
        time.sleep(2.5)
        f = b.capture.grab()
        cv2.imwrite("scratch/npc_dialog.png", cv2.resize(f, None, fx=0.5, fy=0.5))
        cv2.imwrite(f"fixtures/raw/npc_dialog_{time.strftime('%H%M%S')}.png", f)
    inp.move(1270, 590)
    b.hotkeys.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
