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
from .controller import BotError, Chicken, Controller, Died, RunTimeout
from .learn import learn_map
from .lk import MapChanged, fingerprint_ok, load_route, run_route
from .io import open_backend
from .killswitch import KillSwitchTripped
from .lifecycle import create_game, ensure_main_menu, save_and_exit
from .session import start_session
from . import state
from .town import (heal_at_ormus, merc_alive, needs_heal, recover_corpse, repair_at_hratli, revive_merc,
                   set_players, town_to_lower_kurast)
from .vision.screen import ScreenClassifier

log = logging.getLogger("bot.run")
RUNS_CSV = ROOT / "runs.csv"
FIELDS = ["start", "duration_s", "result", "chests", "picked", "error"]


def one_run(bot: Controller, cfg: dict, mode: str, repair: bool = False, buy_keys: bool = False,
            players: int | None = None, corpse: bool = True, stow: bool = False) -> dict:
    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    if mode != "lifecycle":
        bot.wait_for("in_game", 10)
        if players:
            set_players(bot, players)
            state.save({**state.load(), "players_window": bot.game_window_id})
        if corpse:  # only after a death (or at session start: the last session may have ended in one)
            recover_corpse(bot)
        if mode == "chests" and bot.merc_revive and not merc_alive(bot):
            log.info("merc is dead -> Asheara")
            bot.merc_revive = revive_merc(bot)  # failed (no gold?) -> don't retry every run
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
        repair = repair or buy_keys  # same vendor
        if needs_heal(bot) or repair:  # town detours end far from the WP -> fresh game after
            if bot.hp is not None and bot.hp < cfg["town"]["heal_below_pct"]:
                log.info("HP %.0f%% at spawn -> heal at Ormus", bot.hp)
                heal_at_ormus(bot)
                if repair:  # Ormus is on the way to Hratli but the route starts at spawn
                    save_and_exit(bot)
                    create_game(bot, cfg["game"]["difficulty"])
            if repair:
                if repair_at_hratli(bot, keys=buy_keys) and buy_keys:
                    bot.keys_left = cfg["town"]["keys_full"]
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
    bot._labels_known = False
    stats: dict = {}
    try:
        if mode in ("lk", "chests"):
            route = load_route(cfg["game"]["route"]) if mode == "chests" else None
            town_to_lower_kurast(bot, arrived_check=(lambda: fingerprint_ok(bot, route)) if route else None,
                                 stow=stow)
        if mode == "chests":
            bot.deadline = bot.clock() + cfg["safety"]["run_timeout_s"]  # Lower Kurast part only
            stats = run_route(bot, route)
        if mode == "lifecycle":
            bot.kill.sleep(1.0)
    finally:
        bot.deadline = None
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
    ap.add_argument("--route", help="override game.route (maps/<route>/route.yaml)")
    ap.add_argument("--relearn", action="store_true",
                    help="on a map change (2 fingerprint misses in a row): learn the new map, then go on")
    ap.add_argument("--max-minutes", type=float, help="don't start a run after this long (ends at the menu)")
    ap.add_argument("--relearn-games", type=int, default=15, help="exploration games when relearning")
    args = ap.parse_args()

    session = start_session()
    cfg = session.cfg
    if args.pick:
        cfg["loot"]["pick"] = args.pick.split(",")
    if state.load().get("route"):  # a map learned after a map change (see --relearn)
        cfg["game"]["route"] = state.load()["route"]
    if args.route:
        cfg["game"]["route"] = args.route
    log.info("route: %s", cfg["game"]["route"])
    backend = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(backend.window, backend.capture, backend.input,
                     ScreenClassifier.from_config(cfg["vision"]["states"]), session.kill, cfg)
    backend.window.focus()
    bot.keys_left = state.load().get("keys_left")  # estimate; None = unknown -> buy on the first run
    log.info("keys left (estimate): %s", bot.keys_left)
    bot.merc_revive = True
    # /players holds until D2R exits, and soaks run as many short sessions on one D2R: once per D2R window.
    bot.game_window_id = getattr(backend.window, "hwnd", None)
    players_due = bot.game_window_id is None or state.load().get("players_window") != bot.game_window_id
    corpse = state.load().get("corpse", True)  # persisted: a session that ended clean has none
    stow = True  # check the inventory at session start, then after runs that picked anything but rejuvs
    new_file = not RUNS_CSV.exists()
    ok = streak = map_misses = 0
    try:
        with open(RUNS_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            if new_file:
                w.writeheader()
            t_start = time.time()
            for i in range(args.runs):
                if args.max_minutes and time.time() - t_start > args.max_minutes * 60:
                    log.info("time budget of %.1f min used; stopping before run %d", args.max_minutes, i + 1)
                    break
                t0 = time.time()
                row = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "result": "ok", "error": ""}
                try:
                    chests = args.mode == "chests"
                    since_repair = state.load().get("runs_since_repair")  # persisted: soaks run in short batches
                    repair = chests and (since_repair is None or since_repair >= cfg["town"]["repair_every"])
                    if chests:
                        state.save({**state.load(), "runs_since_repair": 0 if repair else (since_repair or 0) + 1})
                    keys = chests and (bot.keys_left is None or bot.keys_left <= cfg["town"]["keys_min"])
                    bot.keys_used = 0
                    try:
                        stats = one_run(bot, cfg, args.mode, repair=repair, buy_keys=keys,
                                        players=cfg["game"].get("players") if players_due and i == 0 else None, corpse=corpse,
                                        stow=stow and chests)
                    finally:  # keys are spent even if the run then chickens
                        if bot.keys_left is not None:
                            bot.keys_left = max(0, bot.keys_left - bot.keys_used)
                        state.save({**state.load(), "keys_left": bot.keys_left})
                    row.update(chests=stats.get("chests", ""), picked=" ".join(stats.get("picked", [])))
                    stow = any(p != "rejuv" for p in stats.get("picked", []))
                    ok += 1
                    streak = map_misses = 0
                    corpse = False
                except MapChanged as e:
                    row.update(result="map_changed", error=str(e))
                    map_misses += 1
                    if not args.relearn:
                        w.writerow({**row, "duration_s": round(time.time() - t0, 1)})
                        log.error("map changed: %s -- stopping; the route needs relearning (--relearn)", e)
                        break
                    if map_misses >= 2:  # twice in a row: not a merc on the platform
                        name = f"auto_{time.strftime('%Y%m%d_%H%M')}"
                        log.warning("map changed twice in a row -> learning it as maps/%s", name)
                        route = learn_map(bot, name, games=args.relearn_games)
                        if route is None:
                            w.writerow({**row, "duration_s": round(time.time() - t0, 1)})
                            log.error("relearning found no super-chest camps; stopping")
                            break
                        cfg["game"]["route"] = name
                        state.save({**state.load(), "route": name})
                        map_misses = 0
                        log.warning("now running the learned route %s: camps %s", name,
                                    [c["world"] for c in route["bonfires"]])
                except (Chicken, Died) as e:
                    row.update(result="chicken" if isinstance(e, Chicken) else "died", error=str(e))
                    log.warning("run %d: %s", i + 1, e)
                    corpse = isinstance(e, Died)
                    stow = True  # it may have picked things before bailing
                except KillSwitchTripped:
                    raise
                except Exception as e:  # noqa: BLE001 - one bad run must not end an unattended soak
                    if not isinstance(e, BotError):
                        log.exception("run %d: unexpected error", i + 1)
                    row.update(result="timeout" if isinstance(e, RunTimeout) else "fail", error=str(e))
                    corpse = stow = True  # a death we didn't see may be behind it
                    streak += 1
                    log.error("run %d failed: %s", i + 1, e)
                state.save({**state.load(), "corpse": corpse})
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
