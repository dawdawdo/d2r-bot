"""Swap Blizzaga into her MF gear from her personal stash (Stephen 2026-11-23: Shako, Chance Guards, Oculus, Gheed's).

  python tools/gear_swap.py [--dry]

Act 3 stash, Personal tab, main weapon set (orb + shield). For each piece: pick it up from the stash, click its
equipment slot (it goes on, the old piece comes to the cursor), click the old piece into the freed stash spot, then
click an empty stash cell as a safety net (anything still on the cursor lands in the stash, never on the ground).
Gheed's Fortune goes to inventory column 0 (rows 0-2). A frame after every step: scratch/gear_swap/. Then save & exit;
check the result in the save (tools: d2save).
Stash grid measured from scratch/stash/stash_personal_tab.png: cell (c, r) top-left (36.6 + 37.8c, 87.6 + 37.8r).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

SX0, SY0, P = 36.6, 87.6, 37.8  # personal stash grid
IX0, IY0 = 867.0, 350.0         # inventory grid (bot/vision/inventory.py)


def stash_center(c: int, r: int, w: int, h: int) -> tuple[int, int]:
    return int(round(SX0 + P * (c + w / 2))), int(round(SY0 + P * (r + h / 2)))


def inv_center(c: int, r: int, w: int, h: int) -> tuple[int, int]:
    return int(round(IX0 + P * (c + w / 2))), int(round(IY0 + P * (r + h / 2)))


# (name, stash cell + size of the MF piece, equipment slot, size of the piece coming off)
SWAPS = [
    ("Harlequin Crest for Kira's Guardian", (8, 8, 2, 2), "helm", (2, 2)),
    ("Chance Guards for Magefist", (6, 8, 2, 2), "gloves", (2, 2)),
    ("The Oculus for Eschuta's Temper", (5, 7, 1, 3), "weapon", (1, 2)),
]
GHEED = (1, 0, 1, 3)           # stash cell of Gheed's Fortune
GHEED_TO = (0, 0, 1, 3)        # inventory cell for it
SAFETY = stash_center(5, 3, 1, 1)  # an empty stash cell


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="open the stash and save frames only")
    args = ap.parse_args()
    out = ROOT / "scratch" / "gear_swap"
    out.mkdir(parents=True, exist_ok=True)
    s = start_session()
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    eq = cfg["inventory"]["equipment"]
    k = [0]

    def shot(name: str) -> None:
        bot.input.move(640, 650)
        bot.kill.sleep(0.35)
        k[0] += 1
        cv2.imwrite(str(out / f"{k[0]:02d}_{name}.png"), bot.capture.grab())

    def click(x: int, y: int, what: str) -> None:
        print(f"  click {what} at ({x}, {y})", flush=True)
        bot.click(x, y)
        bot.kill.sleep(0.6)

    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from stash_look import to_stash

        to_stash(bot, cfg)
        bot.click(*cfg["stash"]["personal_tab"])
        bot.kill.sleep(0.6)
        shot("start")
        if args.dry:
            return 0
        for name, (c, r, w, h), slot, (ow, oh) in SWAPS:
            print(name, flush=True)
            click(*stash_center(c, r, w, h), "the MF piece in the stash")
            click(*eq[slot], f"the {slot} slot")
            click(*stash_center(c, r, ow, oh), "the old piece into the freed stash spot")
            click(*SAFETY, "an empty stash cell (safety)")
            shot(slot)
        print("Gheed's Fortune to the inventory", flush=True)
        click(*stash_center(*GHEED), "Gheed's Fortune in the stash")
        click(*inv_center(*GHEED_TO), "inventory column 0")
        click(*SAFETY, "an empty stash cell (safety)")
        shot("gheed")
        bot.press("esc")
        bot.kill.sleep(0.4)
        print(f"frames in {out}", flush=True)
    except BotError as e:
        print(f"error: {e}", flush=True)
    finally:
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
