"""Dev probe: one LK run; at every chest spot, hover-scan a wide grid around the chest first and save every
tooltip that isn't a chest (looking for "Armor Stand" / "Weapon Rack"). Then the run goes on as normal and
ends with save & exit.

  timeout -s INT 900 python tools/rack_probe.py
Output: scratch/racks/<target>_<wx>_<wy>.png crops + scratch/racks/found.json (world position per tooltip).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import lk  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.tasks.lk import LowerKurast  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402
from bot.vision.tooltip import find_tooltip  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "scratch" / "racks"
import os

RADIUS, RADIUS_Y, STEP = int(os.environ.get("PROBE_R", 330)), int(os.environ.get("PROBE_RY", 330)), int(os.environ.get("PROBE_STEP", 30))
ONLY = os.environ.get("PROBE_ONLY", "")  # e.g. "nw": scan only targets whose name contains it (2026-11-21 Armor Rack hunt)
RACK_TPL = cv2.imread(str(Path(__file__).resolve().parent.parent / "bot/assets/templates/tt_weapon_rack.png"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s = start_session(backup=True)
    cfg = s.cfg
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]), s.kill, cfg)
    b.window.focus()
    found: list[dict] = []
    orig = lk.open_chest
    state = {"target": "?"}

    def scan_then_open(bot, x, y, radius=220, step=35, click=True, odo=None):
        if odo is not None and not odo.lost and click and ONLY in state['target']:
            seen = []
            cv2.imwrite(str(OUT / f"view_{state['target']}.jpg"), bot.capture.grab())
            rack = None
            for dy in range(-RADIUS_Y, RADIUS_Y + 1, STEP):
                for dx in range(-RADIUS, RADIUS + 1, STEP):
                    px, py = x + dx, y + dy
                    if not (20 < px < 1260 and 70 < py < 560):
                        continue
                    bot.check()
                    bot.input.move(px, py)
                    bot.kill.sleep(0.09)
                    f = bot.capture.grab()
                    box = find_tooltip(f, px, py)
                    if box is None or lk._is_chest(f, box):
                        continue
                    if any(abs(box[0] - q[0]) < 8 and abs(box[1] - q[1]) < 8 for q in seen):
                        continue
                    seen.append(box)
                    wx, wy = odo.pos[0] + px - lk.CENTER[0], odo.pos[1] + py - lk.CENTER[1]
                    bx, by, bw, bh = box
                    name = f"{state['target']}_{int(wx)}_{int(wy)}"
                    cv2.imwrite(str(OUT / f"{name}.png"), f[by:by + bh, bx:bx + bw])
                    found.append({"target": state["target"], "world": [round(wx), round(wy)], "box": list(map(int, box)),
                                  "screen": [px, py], "chest_screen": [x, y], "crop": name})
                    print("tooltip", name, box, flush=True)
                    c = cv2.copyMakeBorder(f[by:by + bh, bx:bx + bw], 2, 2, 2, 2, cv2.BORDER_REPLICATE)
                    if RACK_TPL.shape[1] <= c.shape[1] and RACK_TPL.shape[0] <= c.shape[0] and \
                            cv2.minMaxLoc(cv2.matchTemplate(c, RACK_TPL, cv2.TM_CCOEFF_NORMED))[1] > 0.8:
                        rack = (px, py)
            if rack is not None:
                bot.click(*rack)
                bot.wait_still(timeout=2.5, min_wait=0.8)
                bot.input.key_down("alt")
                bot.kill.sleep(0.5)
                cv2.imwrite(str(OUT / f"rackdrop_{state['target']}.jpg"), bot.capture.grab())
                bot.input.key_up("alt")
                print("clicked rack at", rack, flush=True)
            (OUT / "found.json").write_text(json.dumps(found, indent=1))
        return orig(bot, x, y, radius=radius, step=step, click=click, odo=odo)

    orig_visit = lk._visit

    def visit(bot, t, *a, **k):
        state["target"] = t["name"]
        return orig_visit(bot, t, *a, **k)

    lk.open_chest = scan_then_open
    lk._visit = visit
    try:
        ensure_main_menu(bot)
        create_game(bot, cfg["game"]["difficulty"])
        bot.wait_for("in_game", 10)
        task = LowerKurast(cfg)
        task.enter(bot)
        bot.deadline = bot.clock() + 900
        stats = lk.run_route(bot, task.route)
        print("stats", stats.get("chests"), stats.get("picked"), flush=True)
    finally:
        try:
            save_and_exit(bot)
        finally:
            bot.release_all()
            s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
