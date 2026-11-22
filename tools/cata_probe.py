"""Catacombs probe (Andariel): waypoint to Catacombs Level 2 and capture what the finder needs.

  python tools/cata_probe.py [--tp "dx,dy,n;..."]

New Hell game -> town -> waypoint Catacombs Level 2 (Act I tab) -> Battle Orders -> frames with the automap off and on
(scratch/cata/: area name for area_catacombs_2.png, automap line colors for the style) -> optional blind teleports with a
frame after each -> ALWAYS save & exit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import to_durance2  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tp", default="", help="dx,dy,n;...: blind teleports after the arrival frames")
    ap.add_argument("--out", default="cata")
    args = ap.parse_args()
    out = ROOT / "scratch" / args.out
    out.mkdir(parents=True, exist_ok=True)
    s = start_session()  # backs up saves
    cfg = s.cfg
    cfg["safety"].update(chicken_hp_pct=35, potion_hp_pct=60)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()

    def shot(name: str) -> None:
        cv2.imwrite(str(out / f"{name}.png"), bot.capture.grab())

    try:
        to_durance2(bot, say=lambda m: print(m, flush=True), dest="wp_catacombs_2", merc=True)
        from bot.town import cast_warcries

        cast_warcries(bot)
        bot.sleep(0.6)
        shot("arrival")
        bot.press("tab")
        for k in range(3):
            bot.kill.sleep(0.5)
            shot(f"arrival_map{k}")
        if args.tp:
            from bot.nav import CENTER, TP_SETTLE, frame_lag, in_play

            i = 0
            for seg in args.tp.split(";"):
                pdx, pdy, pn = (int(v) for v in seg.split(","))
                pdx, pdy = in_play(pdx, pdy)
                for _ in range(pn):
                    bot.click(int(CENTER[0] + pdx), int(CENTER[1] + pdy), "right", hover=0)
                    bot.sleep(TP_SETTLE + frame_lag(bot) + 0.3)
                    i += 1
                    shot(f"tp{i:02d}")
                    print(f"tp {i}: HP {bot.hp or 0:.0f}% MP {bot.mp or 0:.0f}%", flush=True)
        print(f"frames in {out}", flush=True)
    except BotError as e:
        print(f"error: {e}", flush=True)
    finally:
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
