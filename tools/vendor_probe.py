"""Vendor test (Stephen 2026-11-13): how often does Hratli (Act 3) sell an Archon Plate? Each game: walk to him, open
Trade, Armor tab, hover every stocked cell and save each distinct tooltip, then save & exit. Buys nothing.

  python tools/vendor_probe.py --games 5

Output: maps/<route>/vendor_probe/<game>/armor.png (the tab), tt_<n>.png (tooltips), names.png (all tooltips
stacked, to read by eye and later to cut an "Archon Plate" name template from).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import leave_other_act, open_hratli, restart_in_act3, spawn_act  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402
from bot.vision.tooltip import find_tooltip  # noqa: E402

ARMOR_TAB = (80, 76)            # first vendor tab (Ormus's trade frame, 2026-11-13: Armor | Weapons | Weapons | Misc)
GRID0, PITCH, N = (55, 105), 37.8, 10   # vendor grid = stash grid geometry (cell centres)


def stocked(frame: np.ndarray, c: int, r: int) -> bool:
    """A stocked cell has the blue-tinted item background; empty ones are near black."""
    x, y = int(GRID0[0] + c * PITCH), int(GRID0[1] + r * PITCH)
    cell = frame[y - 12 : y + 12, x - 12 : x + 12]
    return float(cell.mean()) > 28


def probe(bot, out: Path) -> int:
    bot.click(*ARMOR_TAB)
    bot.kill.sleep(0.8)
    bot.input.move(640, 650)
    bot.kill.sleep(0.3)
    tab = bot.capture.grab()
    cv2.imwrite(str(out / "armor.png"), tab)
    seen: list[np.ndarray] = []
    crops = []
    for r in range(N):
        for c in range(N):
            if not stocked(tab, c, r):
                continue
            x, y = int(GRID0[0] + c * PITCH), int(GRID0[1] + r * PITCH)
            bot.input.move(x, y)
            bot.kill.sleep(0.18)
            f = bot.capture.grab()
            box = find_tooltip(f, x, y, half_w=260, max_w=520)
            if box is None:
                continue
            bx, by, bw, bh = box
            crop = f[by : by + min(bh, 40), bx : bx + bw]  # the name line(s) at the top
            if any(s.shape == crop.shape and float(np.abs(s.astype(int) - crop.astype(int)).mean()) < 6 for s in seen):
                continue  # same item, another of its cells
            seen.append(crop)
            cv2.imwrite(str(out / f"tt_{len(seen):02d}_{c}_{r}.png"), f[by : by + bh, bx : bx + bw])
            crops.append(crop)
    if crops:
        w = max(cr.shape[1] for cr in crops)
        sheet = np.vstack([cv2.copyMakeBorder(cr, 2, 2, 0, w - cr.shape[1], cv2.BORDER_CONSTANT) for cr in crops])
        cv2.imwrite(str(out / "names.png"), sheet)
    return len(crops)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1)
    args = ap.parse_args()
    s = start_session()  # backs up saves
    cfg = s.cfg
    root = ROOT / "maps" / cfg["game"]["route"] / "vendor_probe"
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    try:
        for n in range(args.games):
            out = root / time.strftime("%m%d-%H%M%S")
            out.mkdir(parents=True, exist_ok=True)
            try:
                ensure_main_menu(bot)
                create_game(bot, cfg["game"]["difficulty"])
                bot.wait_for("in_game", 10)
                act = spawn_act(bot)
                if act == 4:
                    restart_in_act3(bot)
                elif leave_other_act(bot, act):
                    pass
                if open_hratli(bot):
                    k = probe(bot, out)
                    print(f"game {n + 1}: {k} armor items -> {out}", flush=True)
                    bot.press("esc")
                    bot.kill.sleep(0.5)
                else:
                    print(f"game {n + 1}: Hratli's trade didn't open", flush=True)
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
