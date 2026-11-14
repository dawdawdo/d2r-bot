"""Ancient Tunnels, step 1: waypoint to the Lost City once and record what it looks like.

  python tools/at_probe.py [--hops 0]

New Hell game -> A3 town -> waypoint -> Act II tab -> Lost City (config ui.wp_lost_city, a guess until
this runs) -> frames to maps/<route>/lost_city_probe/: the Act II tab just before the click, the arrival
view, the automap (its top-right area name becomes area_lost_city.png), then `--hops` teleports in a
square with a frame after each -> ALWAYS save & exit. The save then sits in Act 2: the next game spawns in
Lut Gholein and the bot's leave_act2 takes it back to Act 3.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import AREA_REGION, ensure_automap, to_durance2  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

SQUARE = [(300, 0), (0, 200), (-300, 0), (0, -200)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hops", type=int, default=0)
    ap.add_argument("--dest", default="wp_lost_city", help="config ui waypoint point (e.g. wp_black_marsh)")
    ap.add_argument("--name", default="lost_city_probe", help="output folder under maps/<route>/")
    args = ap.parse_args()
    s = start_session()  # backs up saves
    cfg = s.cfg
    out = ROOT / "maps" / cfg["game"]["route"] / args.name
    out.mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    click_ui = bot.click_ui

    def spy(name: str) -> None:  # the tab as it looks right before we pick the Lost City
        if name == args.dest:
            cv2.imwrite(str(out / "wp_tab.png"), bot.capture.grab())
        click_ui(name)

    bot.click_ui = spy
    try:
        to_durance2(bot, say=lambda m: print(m, flush=True), dest=args.dest)
        bot.sleep(2.0)
        f = bot.capture.grab()
        cv2.imwrite(str(out / "arrival.png"), f)
        m = ensure_automap(bot)
        cv2.imwrite(str(out / "arrival_automap.png"), m)
        x, y, w, h = AREA_REGION
        cv2.imwrite(str(out / "area_name.png"), m[y : y + h, x : x + w])
        bot.press("tab")
        print(f"arrived: HP {bot.hp}% MP {bot.mp}%; frames in {out}", flush=True)
        from bot.nav import Odometer, hop

        odo = Odometer(bot.capture.grab())
        for i in range(args.hops):
            dx, dy = SQUARE[i % 4]
            hop(bot, odo, dx, dy)
            cv2.imwrite(str(out / f"hop_{i:02d}.png"), bot.capture.grab())
            print(f"hop {i}: odometry {odo.pos.round().tolist()} resp {odo.resp:.2f} HP {bot.hp}%", flush=True)
            if (bot.hp or 100) < 80:
                break
    except BotError as e:
        print(f"stopped: {e}", flush=True)
    finally:
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
