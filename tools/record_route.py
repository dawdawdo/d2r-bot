"""Record Stephen's trip from the Durance 2 waypoint to the Level 3 stairs (bot/teach.py).

  python tools/record_route.py

The bot makes a Hell game and takes the waypoint to Durance of Hate Level 2 with the automap on, then
hands over: Stephen teleports (right-click) to the stairs and clicks them, as he'd normally play.
Every click is recorded with the view after it. Press F10 once on Level 3 (or to give up): the bot
saves the route to maps/<route>/durance2_route/ and does save & exit. F12 still stops everything.
"""
from __future__ import annotations

import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.durance import AutomapOdometer, ensure_automap, to_durance2  # noqa: E402
from bot.io import open_backend, open_clicks  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.teach import RouteRecorder  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


def main() -> int:
    s = start_session()  # backs up saves
    cfg = s.cfg
    maps = ROOT / "maps" / cfg["game"]["route"]
    folder = maps / "durance2_route"
    if folder.exists():
        shutil.move(str(folder), str(folder.with_name(f"durance2_route_{time.strftime('%Y%m%d-%H%M%S')}")))
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    done = threading.Event()
    b.hotkeys.start("f10", done.set)
    clicks = open_clicks()
    rec = None
    try:
        to_durance2(bot)
        bot.sleep(2.0)  # the "Entering ..." banner fades
        odo = AutomapOdometer.load(maps / "durance2_auto", ensure_automap(bot))  # the searched canvas
        bot.guard(False)  # Stephen plays: no potions or chickens from the bot
        x, y, _, _ = b.window.client_rect()
        rec = RouteRecorder(b.capture, odo, (x, y), folder)
        clicks.start(rec.on_click)
        print("\n*** YOUR TURN: teleport to the Level 3 stairs and click them. Keep the automap (Tab) on.\n"
              "*** Press F10 when you're on Level 3 (or to give up). F12 = emergency stop.\n", flush=True)
        while not done.is_set():
            bot.kill.sleep(0.2)
        clicks.stop()
        steps = rec.finish(b.capture.grab())
        rec = None
        print(f"recorded {len(steps)} clicks ({sum(st['lost'] for st in steps)} without an automap fix) "
              f"-> {folder}", flush=True)
        print("hands off the mouse: save & exit in 2 s", flush=True)
        bot.sleep(2.0)
        save_and_exit(bot)
    finally:
        clicks.stop()
        if rec is not None:
            rec.finish()
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
