"""Catacombs Level 4 probe (Andariel): learned route down, then blind hops with a frame after each.

  python tools/andy_probe.py --hops "-300,150,6" [--out andy]

New Hell game -> waypoint Catacombs 2 -> learned stairs to Level 3 and Level 4 (bot/tasks/andariel.py) -> Battle Orders
-> hops (dx,dy,n;... screen px from her) -> scratch/<out>/: hNN.png (automap hidden) and hNN_map.png -> ALWAYS save & exit.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import durance  # noqa: E402
from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hops", default="-300,150,6")
    ap.add_argument("--out", default="andy")
    ap.add_argument("--names", action="store_true", help="after the hops: hover a grid and save monster name bars")
    args = ap.parse_args()
    out = ROOT / "scratch" / args.out
    out.mkdir(parents=True, exist_ok=True)
    s = start_session()
    cfg = s.cfg
    cfg["safety"].update(chicken_hp_pct=35, potion_hp_pct=60)
    durance.DURANCE_HEAL = 60
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        from bot.nav import CENTER, TP_SETTLE, frame_lag, in_play
        from bot.tasks.andariel import LEVELS, down_a_level
        from bot.town import cast_buffs, cast_warcries

        durance.to_durance2(bot, say=lambda m: print(m, flush=True), dest="wp_catacombs_2", merc=True)
        cast_warcries(bot)
        for folder, here, goal in LEVELS:
            down_a_level(bot, cfg, folder, here, goal)
        print(f"on Level 4: HP {bot.hp or 0:.0f}%", flush=True)
        cast_warcries(bot)
        cast_buffs(bot)
        k = 0

        def shot() -> None:
            f = bot.capture.grab()
            cv2.imwrite(str(out / f"h{k:02d}_map.png"), f)
            bot.press("tab")
            bot.kill.sleep(0.35)
            cv2.imwrite(str(out / f"h{k:02d}.png"), bot.capture.grab())
            bot.press("tab")
            bot.kill.sleep(0.2)

        durance.ensure_automap(bot)
        shot()
        for seg in args.hops.split(";"):
            dx, dy, n = (int(v) for v in seg.split(","))
            dx, dy = in_play(dx, dy)
            for _ in range(n):
                bot.check()
                bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
                bot.sleep(TP_SETTLE + frame_lag(bot) + 0.25)
                k += 1
                shot()
                print(f"hop {k}: HP {bot.hp or 0:.0f}% MP {bot.mp or 0:.0f}%", flush=True)
        if args.names:  # hover a grid; save each monster name bar seen (Andariel's has her name)
            from bot.vision.namebar import name_bar

            seen = 0
            for y in range(90, 560, 45):
                for x in range(120, 1180, 60):
                    bot.check()
                    bot.input.move(x, y)
                    bot.kill.sleep(0.06)
                    f = bot.capture.grab()
                    nb = name_bar(f)
                    if nb is not None:
                        cv2.imwrite(str(out / f"name_{x}_{y}_{nb['life']:.2f}.png"), f[8:70, 440:840])
                        seen += 1
            bot.input.move(1270, 590)
            print(f"{seen} name bars", flush=True)
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
