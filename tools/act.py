"""Send one or more inputs to the game (client coords), then optionally peek.

  python tools/act.py key:esc click:640,360 rclick:100,100 wait:1.5 move:10,10 hold:alt:2 -o shot.png

Uses GuardedInput (F12 kill switch, user-mouse guard, foreground-only).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.io import GuardedInput, open_backend  # noqa: E402
from bot.killswitch import KillSwitch  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("actions", nargs="*")
    ap.add_argument("-o", "--out")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--save-raw", metavar="LABEL")
    args = ap.parse_args()

    cfg = load_config()
    b = open_backend(cfg["game"]["window_title"])
    kill = KillSwitch()
    b.hotkeys.start(cfg["hotkeys"]["kill_switch"], lambda: kill.trip("F12"))
    inp = GuardedInput(b.input, kill)
    if not b.window.is_foreground():
        b.window.focus()
        time.sleep(0.3)
    try:
        for a in args.actions:
            kind, _, rest = a.partition(":")
            if kind == "key":
                inp.press(rest)
            elif kind in ("click", "rclick"):
                x, y = map(int, rest.split(","))
                inp.click(x, y, "right" if kind == "rclick" else "left")
            elif kind == "move":
                inp.move(*map(int, rest.split(",")))
            elif kind == "hold":
                key, secs = rest.rsplit(":", 1)
                inp.key_down(key)
                kill.sleep(float(secs))
                inp.key_up(key)
            elif kind == "wait":
                kill.sleep(float(rest))
            else:
                raise SystemExit(f"bad action {a}")
            time.sleep(0.15)
        if args.out or args.save_raw:
            frame = b.capture.grab()
            if args.save_raw:
                raw = Path(cfg["paths"]["raw_frames"])
                raw.mkdir(parents=True, exist_ok=True)
                p = raw / f"{args.save_raw}_{time.strftime('%Y%m%d-%H%M%S')}.png"
                cv2.imwrite(str(p), frame)
                print("raw:", p)
            if args.out:
                Path(args.out).parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(args.out, cv2.resize(frame, None, fx=args.scale, fy=args.scale,
                                                 interpolation=cv2.INTER_AREA))
                print(f"frame {frame.shape[1]}x{frame.shape[0]} -> {args.out}")
    finally:
        inp.release_all()
        b.hotkeys.stop()
        b.capture.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
