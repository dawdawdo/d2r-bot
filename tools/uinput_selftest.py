"""Live check of the Linux uinput backend (moves YOUR mouse; no clicks or key presses).

Moves the cursor to a few screen points through the virtual absolute pointer, reports where
X says it landed, then puts the cursor back. Run with no game needed:
    /data/AutoDev/miniconda3/envs/d2r/bin/python tools/uinput_selftest.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.io.base import Window  # noqa: E402
from bot.io.linux import UinputInput  # noqa: E402


class Screen(Window):
    def client_rect(self):
        return 0, 0, 0, 0

    def is_foreground(self):
        return True

    def focus(self):
        pass


def main() -> int:
    inp = UinputInput(Screen())
    start = inp._xquery()
    worst = 0
    try:
        for x, y in [(100, 100), (inp.sw // 2, inp.sh // 2), (inp.sw - 101, inp.sh - 101), (640, 360), (1279, 719)]:
            inp._warp(x, y)  # raw, uncorrected: measures the device mapping itself
            time.sleep(0.05)
            px, py = inp._xquery()
            err = max(abs(px - x), abs(py - y))
            worst = max(worst, err)
            print(f"target ({x:4d},{y:4d}) -> X pointer ({px:4d},{py:4d})  error {err}px")
    finally:
        inp._warp(*start)
        inp.close()
    print("OK" if worst <= 1 else f"MAPPING OFF by up to {worst}px (move() corrects once; check the axis range)")
    return 0 if worst <= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
