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
from .controller import BotError, Chicken, Controller, Died, GameSkipped, RunTimeout
from .learn import learn_map
from .lk import MapChanged, TerrorZone
from .tasks import catalog, get_tasks
from .io import open_backend
from .killswitch import KillSwitchTripped
from .lifecycle import create_game, ensure_main_menu, save_and_exit
from .session import start_session
from . import control, state, supplies
from .gamesettings import ensure_loot_filter, ensure_options, large_font_ok, players_setting
from .town import (ensure_main_weapons, leave_act1, leave_other_act, belt_needs_restock, count_keys, durability_ok, heal_at_ormus, merc_alive, needs_heal, recover_corpse,
                   repair_at_hratli, restart_in_act3, revive_merc, set_players, spawn_act, stowaway,
                   town_to_lower_kurast)
from .vision.screen import ScreenClassifier

log = logging.getLogger("bot.run")
RUNS_CSV = ROOT / "runs.csv"
MERC_RETRY_RUNS = 1   # after a failed revive, try again the next run: his Insight is her mana regen (Stephen
                      # 2026-11-08: "the merc is dead, so she's not getting any regen; that's why LK is failing")
MERC_MAX_FAILS = 3    # this many in a row (no gold?): wait MERC_PAUSE_RUNS, then start over
MERC_PAUSE_RUNS = 10
FIELDS = ["start", "duration_s", "result", "chests", "picked", "error", "task"]


def one_run(bot: Controller, cfg: dict, mode: str, repair: bool = False, buy_keys: bool = False,
            players: int | None = None, corpse: bool = True, stow: bool = False,
            check_durability: bool = False, tasks=()) -> dict:
    ensure_main_menu(bot)
    create_game(bot, cfg["game"]["difficulty"])
    if mode != "lifecycle":
        bot.wait_for("in_game", 10)
        if players and set_players(bot, players):
            bot.players_now = players
            state.save({**state.load(), "players_window": bot.game_window_id, "players_n": players})
        ensure_loot_filter(bot)  # Stephen may have picked his own filter while playing
        if corpse:  # only after a death (or at session start: the last session may have ended in one)
            recover_corpse(bot)
        ensure_main_weapons(bot)
        bot.act = spawn_act(bot) if mode == "chests" else 3
        if leave_other_act(bot, bot.act):  # Stephen's own game ended in Act 1 or 2
            bot.act = spawn_act(bot)
        log.info("spawn: act %d, HP %.0f%% MP %.0f%%", bot.act, bot.hp or 0, bot.mp or 0)
        if not bot.merc_revive:
            bot.merc_wait = getattr(bot, "merc_wait", 0) - 1
            bot.merc_revive = bot.merc_wait <= 0
            if bot.merc_revive and getattr(bot, "merc_fails", 0) >= MERC_MAX_FAILS:
                bot.merc_fails = 0  # the pause is over: a fresh set of tries
        if bot.act == 4 and stow:  # extra key stacks can be dropped here; loot for the stash can't
            stow = stowaway(bot, stash=False) is None
        if bot.act == 4 and (stow or repair or buy_keys or needs_heal(bot) or belt_needs_restock(bot)
                             or (bot.merc_revive and not merc_alive(bot)) or state.load().get("gold_needed")):
            restart_in_act3(bot)  # stash and vendors are all in Act 3
            bot.act = 3
        if mode == "chests" and bot.merc_revive and not merc_alive(bot):
            log.info("merc is dead -> Asheara")
            if revive_merc(bot):
                bot.merc_fails = 0
            else:  # not found / no gold: retry after MERC_RETRY_RUNS (2026-11-01 one miss at 21:55 left her
                # without a merc all night: chickens 1% -> 11%, 2 deaths); give up after MERC_MAX_FAILS in a row
                bot.merc_fails = getattr(bot, "merc_fails", 0) + 1
                bot.merc_revive = False
                bot.merc_wait = MERC_PAUSE_RUNS if bot.merc_fails >= MERC_MAX_FAILS else MERC_RETRY_RUNS
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
            bot.wait_for("in_game", 10)
        if check_durability and not repair:
            st = state.load()
            if not durability_ok(bot):  # first wear seen: ~1 point per 10 runs, the Shako has 12
                st["repair_due"] = cfg["town"]["repair_after_wear"]
                log.info("wear seen; repairing in %d runs", st["repair_due"])
            state.save({**st, "runs_since_dur_check": 0})
        if buy_keys:
            n = count_keys(bot)
            if n is not None and n >= 3:  # 3 = "3 to 9": count it as 6
                bot.keys_left, buy_keys = (n if n >= 10 else 6), False
                log.info("keys: at least %d in the inventory (estimate was low); not buying", n)
        repair = repair or buy_keys  # same vendor
        if needs_heal(bot) or repair:  # town detours end far from the WP -> fresh game after
            if bot.hp is not None and bot.hp < cfg["town"]["heal_below_pct"]:
                log.info("HP %.0f%% at spawn -> heal at Ormus", bot.hp)
                if not heal_at_ormus(bot):  # he wanders: once more from a fresh spawn (2026-11-02 10:02: a miss
                    log.info("Ormus missed; again in a fresh game")  # sent her to LK at 33%: instant chicken)
                    save_and_exit(bot)
                    create_game(bot, cfg["game"]["difficulty"])
                    bot.wait_for("in_game", 10)
                    if not heal_at_ormus(bot):
                        raise BotError(f"not healed (HP {bot.hp:.0f}%): Ormus not found twice")
                if repair:  # Ormus is on the way to Hratli but the route starts at spawn
                    save_and_exit(bot)
                    create_game(bot, cfg["game"]["difficulty"])
            if repair:
                st = {k: v for k, v in state.load().items() if k != "repair_due"}
                state.save({**st, "runs_since_repair": 0, "runs_since_dur_check": 0})
                repair_at_hratli(bot, keys=buy_keys)  # buy_keys sets keys_left from the stack it reads
            save_and_exit(bot)
            create_game(bot, cfg["game"]["difficulty"])
    bot._labels_known = False
    stats: dict = {}
    try:
        if mode == "lk":  # M3 check: town -> Lower Kurast only
            town_to_lower_kurast(bot)
        if mode == "chests":
            stats = run_tasks(bot, tasks, stow)
        if mode == "lifecycle":
            bot.kill.sleep(1.0)
    finally:
        bot.deadline = None
        if bot.state != "main_menu":
            save_and_exit(bot)
    return stats


def run_tasks(bot: Controller, tasks, stow: bool) -> dict:
    """The game's tasks in order (bot/tasks): the first from town, each next one from the waypoint the
    previous one ended at. Stats are summed; a failed hand-off skips the rest of the game."""
    stats: dict = {"chests": 0, "picked": []}
    for k, task in enumerate(tasks):
        if k and not stats.get("chained"):
            log.info("no hand-off to %s; ending the game", task.name)
            break
        stats.pop("chained", None)
        task.enter(bot, stow=stow, chained=k > 0)
        s = task.farm(bot)
        stats["chests"] += s.get("chests", 0)
        stats["picked"] += s.get("picked", [])
        stats.update({key: v for key, v in s.items() if key not in ("chests", "picked")})
    return stats


def _upgrade_header() -> None:
    """runs.csv predates some columns: rewrite its header line to FIELDS (rows only ever gain columns)."""
    if not RUNS_CSV.exists():
        return
    lines = RUNS_CSV.read_text().splitlines(True)
    if lines and lines[0].strip() != ",".join(FIELDS):
        lines[0] = ",".join(FIELDS) + "\n"
        RUNS_CSV.write_text("".join(lines))


def runes_only(cfg: dict) -> bool:
    """Full stash: what's picked now can't be stored and would crowd runes out of the inventory (only ~13 free
    cells). Runes still go to their own tab. True if this changed anything."""
    loot = cfg["loot"]
    if loot["pick"] == ["rune"] and not loot.get("pick_white_other"):
        return False
    loot["pick"], loot["pick_white_other"] = ["rune"], False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--max-fail-streak", type=int, default=3)
    ap.add_argument("--mode", choices=["lifecycle", "lk", "chests"], default="lifecycle",
                    help="lifecycle = M2 create/exit; lk = M3 town -> Lower Kurast; "
                         "chests = M4/M5 full run (route, chests, loot)")
    ap.add_argument("--pick", help="override loot.pick, e.g. rune,unique,white (testing)")
    ap.add_argument("--route", help="override game.route (maps/<route>/route.yaml)")
    ap.add_argument("--task", "--tasks", dest="tasks", default="lk",
                    help="farming tasks for --mode chests, comma-separated: all of them in each game, in "
                         "catalog order (bot/tasks)")
    ap.add_argument("--relearn", action="store_true",
                    help="on a map change (2 fingerprint misses in a row): learn the new map, then go on")
    ap.add_argument("--max-minutes", type=float, help="don't start a run after this long (ends at the menu)")
    ap.add_argument("--relearn-games", type=int, default=15, help="exploration games when relearning")
    ap.add_argument("--no-act4", action="store_true", help="end every run in LK (new games start in Act 3)")
    ap.add_argument("--stash-full-ok", action="store_true",
                    help="a full stash doesn't end the session: pick up only runes from then on (they have their own tab)")
    args = ap.parse_args()

    session = start_session()
    cfg = session.cfg
    if args.no_act4:
        cfg["game"]["act4_exit"] = False
    if args.pick:
        cfg["loot"]["pick"] = args.pick.split(",")
    if state.load().get("route"):  # a map learned after a map change (see --relearn)
        cfg["game"]["route"] = state.load()["route"]
    if args.route:
        cfg["game"]["route"] = args.route
    log.info("route: %s", cfg["game"]["route"])
    tasks = get_tasks(args.tasks.split(","), cfg) if args.mode == "chests" else []
    log.info("tasks: %s", ", ".join(t.name for t in tasks) or "-")
    lk_ready = any(t["name"] == "lk" and t["ready"] for t in catalog(cfg))
    has_boss = any(t.name != "lk" for t in tasks)
    refill_tasks = get_tasks(["lk"], cfg) if has_boss and lk_ready else []
    supplies.new_session()
    backend = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(backend.window, backend.capture, backend.input,
                     ScreenClassifier.from_config(cfg["vision"]["states"]), session.kill, cfg)
    from .lifecycle import windowed

    if not windowed(backend.window, backend.input, cfg["game"]["resolution"]):  # Stephen resizes it when he plays
        log.warning("window size is not %s", cfg["game"]["resolution"])
    backend.window.focus()
    bot.keys_left = state.load().get("keys_left")  # estimate; None = unknown -> buy on the first run
    log.info("keys left (estimate): %s", bot.keys_left)
    bot.merc_revive = True
    # /players holds until D2R exits, and soaks run as many short sessions on one D2R: once per D2R window.
    bot.game_window_id = getattr(backend.window, "hwnd", None) or getattr(backend.window, "wid", None)  # Win32 / X11
    want_players = supplies.players_for(tasks, cfg)
    st0 = state.load()  # which value too: a window id alone let a Meph session run at LK's 7 (2026-11-08)
    players_due = (bot.game_window_id is None or st0.get("players_window") != bot.game_window_id
                   or st0.get("players_n") != want_players)
    if players_setting(cfg) == want_players:
        players_due = False  # D2R keeps /players as a setting: no typing needed
        bot.players_now = want_players  # known, so a later switch of tasks retypes it
    if large_font_ok(cfg) is False:  # every panel coordinate assumes it; clicking on would hit the wrong spots
        session.kill.trip("Large Font Mode is off (Options > Gameplay > Accessibility): panels won't line up")
        session.kill.check()
    try:
        ensure_main_menu(bot)
        ensure_options(bot)  # automap as the bot needs it, whatever Stephen set while playing
    except BotError as e:
        log.warning("game options not checked: %s", e)
    corpse = state.load().get("corpse", True)  # persisted: a session that ended clean has none
    stow = True  # check the inventory at session start, then after runs that picked anything but rejuvs
    new_file = not RUNS_CSV.exists()
    ok = streak = map_misses = 0
    tally: dict[str, int] = {}
    stop = False
    control.clear()  # a request left over from an earlier session
    t_start = time.time()
    _upgrade_header()
    try:
        with open(RUNS_CSV, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS)
            if new_file:
                w.writeheader()
            for i in range(args.runs):
                if args.max_minutes and time.time() - t_start > args.max_minutes * 60:
                    log.info("time budget of %.1f min used; stopping before run %d", args.max_minutes, i + 1)
                    break
                if stop or control.read():
                    log.info("stop requested (web page); not starting run %d", i + 1)
                    break
                active = supplies.tasks_for_run(tasks, refill_tasks, cfg)  # a dry rejuv stash: LK instead
                bot.no_potions = supplies.saving_rejuvs(active, refill_tasks, cfg)
                want_players = supplies.players_for(active, cfg)
                task_name = "+".join(t.name for t in active) or args.mode
                control.write_status(state="running", run=i + 1, runs=args.runs, task=task_name,
                                     tally=tally, started=t_start)
                t0 = time.time()
                row = {"start": time.strftime("%Y-%m-%d %H:%M:%S"), "result": "ok", "error": "",
                       "task": task_name}
                try:
                    chests = args.mode == "chests"
                    since_repair = state.load().get("runs_since_repair")  # persisted: soaks run in short batches
                    due = state.load().get("repair_due")
                    repair = chests and (since_repair is None or since_repair >= cfg["town"]["repair_every"]
                                         or (due is not None and due <= 0))
                    if chests and due is not None:
                        state.save({**state.load(), "repair_due": due - 1})
                    since_dur = state.load().get("runs_since_dur_check")
                    dur = chests and due is None and (since_dur is None or since_dur >= cfg["town"]["durability_every"])
                    if chests:
                        state.save({**state.load(), "runs_since_repair": 0 if repair else (since_repair or 0) + 1,
                                    "runs_since_dur_check": 0 if repair else (since_dur or 0) + 1})
                    # the next run repairs (Act 3): this one shouldn't end in Act 4 (tasks/lk.py town_due)
                    bot.repair_next = chests and not repair and (
                        (since_repair or 0) + 1 >= cfg["town"]["repair_every"] or (due is not None and due - 1 <= 0))
                    keys = chests and (bot.keys_left is None or bot.keys_left <= cfg["town"]["keys_min"])
                    bot.keys_used = 0
                    bot.died_on_exit = False
                    try:
                        stats = one_run(bot, cfg, args.mode, repair=repair, buy_keys=keys,
                                        players=want_players if (players_due and i == 0) or getattr(bot, "players_now", None)
                                        not in (None, want_players) else None, corpse=corpse,  # Meph sets its own
                                        stow=stow and chests, check_durability=dur, tasks=active)
                    finally:  # keys are spent even if the run then chickens
                        if bot.keys_left is not None:
                            bot.keys_left = max(0, bot.keys_left - bot.keys_used)
                        state.save({**state.load(), "keys_left": bot.keys_left})
                    row.update(chests=stats.get("chests", ""), picked=" ".join(stats.get("picked", [])))
                    stow = any(p != "rejuv" for p in stats.get("picked", []))
                    ok += 1
                    streak = map_misses = 0
                    corpse = False
                except TerrorZone as e:  # wait at the menu for the zone to rotate (top of the hour)
                    row.update(result="terror", error=str(e))
                    now = time.time()
                    until = now - now % 3600 + 3600 + 60
                    if args.max_minutes:
                        until = min(until, t_start + 60 * args.max_minutes)
                    log.warning("%s: waiting %.0f min (save & exit done)", e, max(0, until - now) / 60)
                    while time.time() < until:
                        session.kill.sleep(5)
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
                        tasks = get_tasks([t.name for t in tasks], cfg)  # reload with the learned route
                        refill_tasks = get_tasks(["lk"], cfg) if refill_tasks else []
                        map_misses = 0
                        log.warning("now running the learned route %s: camps %s", name,
                                    [c["world"] for c in route["bonfires"]])
                except (Chicken, Died) as e:
                    died = isinstance(e, Died) or getattr(bot, "died_on_exit", False)
                    row.update(result="died" if died else "chicken", error=str(e))
                    log.warning("run %d: %s%s", i + 1, e, " (died before the exit)" if died and isinstance(e, Chicken) else "")
                    corpse = died
                    stow = True  # it may have picked things before bailing
                except KillSwitchTripped:
                    raise
                except control.StopNow:  # save & exit already happened in one_run's finally
                    row.update(result="stopped", error="stop requested from the web page")
                    stop = True
                except GameSkipped as e:  # not a failure: must not count toward stopping the session
                    row.update(result="skipped", error=str(e))
                    log.info("run %d skipped: %s", i + 1, e)
                    stow = True  # the LK part may have picked things
                    streak = 0
                except Exception as e:  # noqa: BLE001 - one bad run must not end an unattended soak
                    if not isinstance(e, BotError):
                        log.exception("run %d: unexpected error", i + 1)
                    died = getattr(bot, "died_on_exit", False)  # a death the exit saw, then failed after
                    row.update(result="died" if died else "timeout" if isinstance(e, RunTimeout) else "fail",
                               error=str(e))
                    corpse = stow = True  # a death we didn't see may be behind it
                    streak += 1
                    log.error("run %d failed: %s", i + 1, e)
                state.save({**state.load(), "corpse": corpse})
                row["duration_s"] = round(time.time() - t0, 1)
                w.writerow(row)
                f.flush()
                log.info("run %d/%d %s in %.1fs", i + 1, args.runs, row["result"], row["duration_s"])
                tally[row["result"]] = tally.get(row["result"], 0) + 1
                tally["chests"] = tally.get("chests", 0) + int(row.get("chests") or 0)
                control.write_status(state="running", run=i + 1, runs=args.runs, task=row["task"], tally=tally,
                                     started=t_start, last=row)
                if getattr(bot, "stash_full", False):
                    if not args.stash_full_ok:
                        log.error("stash full, loot can't be stored: stopping (Stephen clears it)")
                        break
                    if runes_only(cfg):
                        log.warning("stash full: picking up only runes from now on")
                if streak >= args.max_fail_streak:
                    log.error("%d failures in a row; stopping", streak)
                    break
    except KillSwitchTripped as e:
        log.warning("stopped by kill switch: %s", e)
        tally["kill switch"] = 1
    finally:
        control.write_status(state="idle", tally=tally, started=t_start)
        control.clear()
        bot.release_all()
        backend.capture.close()
        session.close()
    log.info("%d/%d runs ok", ok, args.runs)
    return 0 if ok == args.runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
