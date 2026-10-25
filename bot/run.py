"""Bot entry point.

  python -m bot.run --runs 20          # M2: create game -> save & exit, N times
  python -m bot.run --runs 5 --mode lk # M3: ... -> town WP -> Lower Kurast -> save & exit

Backs up saves first, arms F12, logs to logs/, appends one row per run to runs.csv.
"""
from __future__ import annotations

import argparse
import csv
import logging
import time

from .config import ROOT
from .controller import BotError, Chicken, Controller, Died
from .lk import MapChanged, load_route, run_route
from .io import open_backend
from .killswitch import KillSwitchTripped
from .lifecycle import create_game, ensure_main_menu, save_and_exit
from .session import start_session
from .town import heal_at_ormus, needs_heal, recover_corpse, town_to_lower_kurast
from .vision.screen import ScreenClassifier

log = logging.getLogger("bot.run")
RUNS_CSV = ROOT / "runs.csv"
FIELDS = ["start", "duration_s", "result", "chests", "picked", "error"]


def one_run(bot: Controller, cfg: dict, mode: str) -> dict:
    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    if mode != "lifecycle":
        bot.wait_for("in_game", 10)
        recover_corpse(bot)
        if needs_heal(bot):
            log.info("HP %.0f%% at spawn -> heal at Ormus, then a fresh game", bot.hp)
            heal_at_ormus(bot)
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
    bot._labels_known = False
    stats: dict = {}
    try:
        if mode in ("lk", "chests"):
            town_to_lower_kurast(bot)
        if mode == "chests":
            stats = run_route(bot, load_route(cfg["game"]["route"]))
        if mode == "lifecycle":
            bot.kill.sleep(1.0)
    finally:
        if bot.state != "main_menu":
            save_and_exit(bot)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-fail-streak", type=int, default=3)
    ap.add_argument("--mode", choices=["lifecycle", "lk", "chests"], default="lifecycle",
                    help="lifecycle = M2 create/exit; lk = M3 town -> Lower Kurast; "
                         "chests = M4/M5 full run (route, chests, loot)")
    ap.add_argument("--pick", help="override loot.pick, e.g. rune,unique,white (testing)")
    args = ap.parse_args()

    session = start_session()
    cfg = session.cfg
    if args.pick:
        cfg["loot"]["pick"] = args.pick.split(",")
    backend = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(backend.window, backend.capture, backend.input,
                     ScreenClassifier.from_config(cfg["vision"]["states"]), session.kill, cfg)
    backend.window.focus()
    new_file = not RUNS_CSV.exists()
    ok = streak = 0
    try:
        with open(RUNS_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            if new_file:
                w.writeheader()
            for i in range(args.runs):
                t0 = time.time()
                row = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "result": "ok", "error": ""}
                try:
                    stats = one_run(bot, cfg, args.mode)
                    row.update(chests=stats.get("chests", ""), picked=" ".join(stats.get("picked", [])))
                    ok += 1
                    streak = 0
                except MapChanged as e:
                    row.update(result="map_changed", error=str(e))
                    w.writerow({**row, "duration_s": round(time.time() - t0, 1)})
                    log.error("map changed: %s -- stopping; the route needs relearning", e)
                    break
                except (Chicken, Died) as e:
                    row.update(result="chicken" if isinstance(e, Chicken) else "died", error=str(e))
                    log.warning("run %d: %s", i + 1, e)
                except BotError as e:
                    row.update(result="fail", error=str(e))
                    streak += 1
                    log.error("run %d failed: %s", i + 1, e)
                row["duration_s"] = round(time.time() - t0, 1)
                w.writerow(row)
                f.flush()
                log.info("run %d/%d %s in %.1fs", i + 1, args.runs, row["result"], row["duration_s"])
                if streak >= args.max_fail_streak:
                    log.error("%d failures in a row; stopping", streak)
                    break
    except KillSwitchTripped as e:
        log.warning("stopped by kill switch: %s", e)
    finally:
        bot.release_all()
        backend.capture.close()
        session.close()
    log.info("%d/%d runs ok", ok, args.runs)
    return 0 if ok == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
