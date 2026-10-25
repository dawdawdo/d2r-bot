"""Save game frames to fixtures/raw/ for labeling.

  python tools/capture.py --label town            # F9 saves one frame, F12 quits
  python tools/capture.py --label lk --interval   # save at config capture.fps until F12

Filenames: <label>_<YYYYmmdd-HHMMSS>_<n>.png. Captures read the screen only; no input sent.
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import load_config  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.killswitch import KillSwitchTripped  # noqa: E402
from bot.session import start_session  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="frame")
    ap.add_argument("--interval", action="store_true", help="save continuously at capture.fps")
    ap.add_argument("--snap-key", default="f9")
    ap.add_argument("--count", type=int, default=0, help="stop after N frames (0 = unlimited)")
    args = ap.parse_args()

    cfg = load_config()
    session = start_session(cfg, backup=False)  # read-only tool: no input, no save access
    backend = open_backend(cfg["game"]["window_title"])
    out = Path(cfg["paths"]["raw_frames"])
    out.mkdir(parents=True, exist_ok=True)

    snap = threading.Event()
    session.hotkeys.start(args.snap_key, snap.set)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    n = 0
    period = 1.0 / float(cfg["capture"]["fps"])
    print(f"capturing '{args.label}' -> {out}  "
          f"({'interval' if args.interval else args.snap_key.upper() + ' to snap'}, F12 to quit)")
    try:
        while True:
            session.kill.check()
            if args.interval or snap.is_set():
                snap.clear()
                frame = backend.capture.grab()
                path = out / f"{args.label}_{stamp}_{n:03d}.png"
                cv2.imwrite(str(path), frame)
                n += 1
                print(f"saved {path.name} {frame.shape[1]}x{frame.shape[0]}")
                if args.count and n >= args.count:
                    break
                if args.interval:
                    session.kill.sleep(period)
                    continue
            session.kill.sleep(0.05)
    except (KillSwitchTripped, KeyboardInterrupt):
        pass
    finally:
        backend.capture.close()
        session.close()
    print(f"done, {n} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
