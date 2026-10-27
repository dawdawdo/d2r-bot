"""Ctrl+left-click points in the game (dev helper): python tools/ctrlclick.py 267,165 924,480"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.io import GuardedInput, open_backend  # noqa: E402
from bot.killswitch import KillSwitch  # noqa: E402

cfg = load_config()
b = open_backend(cfg["game"]["window_title"])
inp = GuardedInput(b.input, KillSwitch())
try:
    for p in sys.argv[1:]:
        x, y = map(int, p.split(","))
        inp.key_down("ctrl")
        time.sleep(0.05)
        inp.click(x, y, "left")
        time.sleep(0.05)
        inp.key_up("ctrl")
        time.sleep(0.35)
    inp.move(640, 600)
finally:
    inp.release_all()
    b.capture.close()
