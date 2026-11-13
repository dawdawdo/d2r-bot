"""Record Stephen's trip through the Durance of Hate (bot/teach.py).

  python tools/record_route.py             # Level 2: waypoint -> Level 3 stairs
  python tools/record_route.py --level 3   # Level 3: stairs arrival -> his Mephisto spot -> the kill
  python tools/record_route.py --level 3 --players 1   # same, /players 1 typed on arrival
  python tools/record_route.py --duriel --players 1    # town -> Canyon -> true tomb -> Duriel (or record_duriel.bat)
  python tools/record_route.py --tunnels               # Lost City WP -> Ancient Tunnels entrance (F9) -> the tunnels

--duriel records from the spawn, so his waypoint clicks are in it too. F9 on arriving in each new area (Canyon,
tomb, Duriel's chamber): each area gets its own automap canvas.

The bot makes a Hell game and takes the waypoint to Durance of Hate Level 2 with the automap on (with
--level 3 it then takes its learned route down the stairs), then hands over: Stephen plays as he
normally would. Every click is recorded with the view after it, and while he holds the right button
a step per cast. Press F10 when done (or to give up): the bot saves the route to
maps/<route>/durance<level>_route/ (Level 3 also gets its automap canvas in canvas/) and does
save & exit. F12 still stops everything.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import Controller  # noqa: E402
from bot.durance import (AutomapOdometer, StopGraph, ensure_automap, level_now, to_durance2, to_level3,  # noqa: E402
                         use_style)
from bot.io import open_backend, open_clicks  # noqa: E402
from bot.gamesettings import ensure_loot_filter, ensure_options  # noqa: E402
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.teach import RouteRecorder  # noqa: E402
from bot.town import recover_corpse, set_players  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402

TASKS = {2: "teleport to the Level 3 stairs and click them",
         3: "go to your Mephisto spot (moat trick) and kill him as you normally would",
         "duriel": "take the waypoint to the Canyon of the Magi, go through the true tomb and kill Duriel as you "
                   "normally would. Press F9 each time you arrive in a new area",
         "tunnels": "teleport to the Ancient Tunnels entrance and go down. Press F9 as soon as you're inside the "
                    "tunnels, then clear them as you normally would (pick up what you want)"}


def start_duriel(bot, players) -> AutomapOdometer:
    """A fresh Hell game, handed over at the spawn."""
    ensure_main_menu(bot)
    ensure_options(bot)  # the automap the odometer reads
    create_game(bot, bot.cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)
    if players and not set_players(bot, players):
        print(f"!!! /players {players} not confirmed: type it yourself in chat", flush=True)
    ensure_loot_filter(bot)
    recover_corpse(bot)
    return AutomapOdometer(ensure_automap(bot))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=2, choices=(2, 3))
    ap.add_argument("--duriel", action="store_true")
    ap.add_argument("--tunnels", action="store_true", help="Lost City -> Ancient Tunnels (F9 inside)")
    ap.add_argument("--players", type=int, default=None, help="/players N before handing over (Meph: 1)")
    args = ap.parse_args()

    s = start_session()  # backs up saves
    cfg = s.cfg
    maps = ROOT / "maps" / cfg["game"]["route"]
    folder = maps / ("duriel_route" if args.duriel else "tunnels_route" if args.tunnels else f"durance{args.level}_route")
    if folder.exists():
        shutil.move(str(folder), str(folder.with_name(f"{folder.name}_{time.strftime('%Y%m%d-%H%M%S')}")))
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    done = threading.Event()
    b.hotkeys.start("f10", done.set)
    leg = threading.Event()
    b.hotkeys.start("f9", leg.set)
    clicks = open_clicks()
    rec = None
    try:
        if args.duriel:
            odo = start_duriel(bot, args.players)
        elif args.tunnels:
            use_style("red")  # the Lost City automap (tools/find_tunnels.py)
            to_durance2(bot, dest="wp_lost_city")
            bot.sleep(2.0)
            odo = AutomapOdometer(ensure_automap(bot))
        else:
            to_durance2(bot)
            bot.sleep(2.0)  # the "Entering ..." banner fades
            auto = maps / "durance2_auto"
            odo = AutomapOdometer.load(auto, ensure_automap(bot))  # the searched canvas
        if args.level == 3 and not (args.duriel or args.tunnels):
            to_level3(bot, odo, StopGraph.load(auto / "graph.json"), None, auto)
            bot.sleep(1.5)
            if level_now(bot) != 3:
                raise SystemExit("not on Level 3")
            if args.players and not set_players(bot, args.players):
                print(f"!!! /players {args.players} not confirmed: type it yourself in chat", flush=True)
            odo = AutomapOdometer(bot.capture.grab())  # a fresh canvas: Level 3 starts here
        bot.guard(False)  # Stephen plays: no potions or chickens from the bot
        x, y, _, _ = b.window.client_rect()

        def cursor():
            p = b.input.cursor_pos()
            return None if p is None else (p[0] + x, p[1] + y)

        rec = RouteRecorder(b.capture, odo, (x, y), folder, cursor=cursor,
                            fresh_odo=AutomapOdometer if (args.duriel or args.tunnels) else None)
        clicks.start(rec.on_click, rec.on_release)
        print(f"\n*** YOUR TURN: {TASKS["duriel" if args.duriel else "tunnels" if args.tunnels else args.level]}. Keep the automap (Tab) on.\n"
              "*** Press F10 when you're done (or to give up). F12 = emergency stop.\n", flush=True)
        while not done.is_set():
            if (args.duriel or args.tunnels) and leg.is_set():
                leg.clear()
                if args.tunnels:
                    use_style("tan")  # inside: a dungeon automap (a guess; the views are saved either way)
                rec.new_leg()
                print("new area marked", flush=True)
            bot.kill.sleep(0.2)
        clicks.stop()
        steps = rec.finish(b.capture.grab())
        finished, rec = rec, None
        if args.duriel or args.tunnels:
            finished.odo.save(folder / f"canvas{finished.leg}")
        elif args.level == 3:
            odo.save(folder / "canvas")
        held = sum(bool(st.get("held")) for st in steps)
        print(f"recorded {len(steps)} steps ({held} while held, {sum(st['lost'] for st in steps)} without "
              f"an automap fix) -> {folder}", flush=True)
        print("hands off the mouse: save & exit in 2 s", flush=True)
        bot.sleep(2.0)
        # He moved the mouse: that's not a grab. The guard is bot.input, not b.input (the raw input),
        # which is why this still tripped on 2026-10-29 and 2026-10-30.
        bot.input.expected = None
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
