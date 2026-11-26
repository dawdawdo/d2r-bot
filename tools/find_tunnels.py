"""Find a level entrance from a waypoint, by the bot alone (first the Ancient Tunnels in the Lost City; the Pit:
  python tools/find_tunnels.py --dest wp_black_marsh --style gray --areas black_marsh --outdoor-any --folder pit_auto --goal pit_level_1)
Originally: find the Ancient Tunnels entrance in the Lost City (the Durance stairs finder,
bot/durance.py, with the red automap style and Lost City area checks).

  python tools/find_tunnels.py --games 5 --hops 60 [--fresh]

Each game: new Hell game -> waypoint Lost City -> automap on -> grow the stop graph toward unexplored
automap, hover-scan new stops for long tooltips ("Ancient Tunnels" over the trapdoor) -> take an untested
one, record where it leads -> ALWAYS save & exit. Resumes from maps/<route>/lost_city_auto/.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import (SCAN, AutomapOdometer, StopGraph, area_is, ensure_automap, explore_game,  # noqa: E402
                         to_durance2, use_style)
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


AREAS = ["lost_city"]  # area templates that mean "still searching" (--areas)
OUTDOOR_ANY = [False]  # --outdoor-any: an unknown area name with this style's automap showing counts too (Black Marsh ->
                       # Tamoe Highland is an open border; the Pit itself is a cave with another automap)


def in_lost_city(bot) -> bool:
    """Still in the searched area(s)? (The name stayed from the Lost City search; now any --areas.)"""
    try:
        f = ensure_automap(bot)
    except BotError:  # this style's automap doesn't show: somewhere else (2026-11-13 10:16: inside the tunnels, tan)
        return False
    if any(area_is(f, a) for a in AREAS):
        return True
    return OUTDOOR_ANY[0]


# 2026-11-13 game 1: a poison pack took her 100 -> 18 % in ~4 s during a 25 s scan at the 3rd stop. Now:
# a coarse grid (~6 s) that aborts on the first few points lost. Game 2: "anything moving" vetoed all 28
# stops and HP sat at 71 % with no regen: skip only below 60 % life (Stephen: some deaths are fine).
# Game 3: movers near her at almost every stop (leapers, beetles, her merc): the Lost City is never quiet, so no
# movers veto; the scan just aborts on the first points lost. The entrance is a Trap Door that starts closed
# (Stephen): a short tooltip, so min_w is low and take_warp re-hovers after a click that didn't leave.
# Game 4: the first one was "Guard Corpse" (138 px). ~11.5 px a letter: "Trap Door" ~104 px, so a band, plus
# durance.is_junk (labels already found to lead nowhere are skipped). "Ancient Tunnels" (~170) once it's open.
SCAN.update(dx=120, dy=80, abort_hp=4, abort_mp=8, min_w=88, max_w=128, every=3, precise=True)
QUIET_HP = 60
DIRS = {"n": (0, -1), "ne": (1, -1), "e": (1, 0), "se": (1, 1), "s": (0, 1), "sw": (-1, 1), "ssw": (-0.6, 1), "w": (-1, 0), "nw": (-1, -1)}  # ssw: the Pit from the Outer Cloister (Stephen 2026-11-14)


# Game 6-8: fighting first (nav.fight) made it worse: it casts at the biggest moving blob, often her merc, while
# she stands in the pack. Now: no fight; struck during a scan -> two hops away from whatever moves near her.
NEAR = 350


BUFFED = [0.0]  # bot.clock() of the last war cries + armor/shield cast


def safe_to_scan(bot) -> bool:
    bot.check()
    if (bot.hp or 100) < QUIET_HP:
        print(f"  no scan: HP {bot.hp:.0f}%", flush=True)
        return False
    # Battle Orders lasts ~90 s and Energy Shield not much longer: every Catacombs chicken frame (2026-11-22) had max
    # life 348 (no BO) and a full mana orb (no shield). Standing still to scan is when she needs them: refresh first.
    if bot.clock() - BUFFED[0] > bot.cfg["hotkeys"].get("warcry_refresh_s", 75):
        from bot.town import cast_buffs, cast_warcries

        cast_warcries(bot)
        cast_buffs(bot)
        BUFFED[0] = bot.clock()
    return True


def evade(bot, odo) -> None:
    """Two hops away from the movers near her (or straight back toward the waypoint if none are seen)."""
    import math

    import numpy as np

    from bot.nav import CENTER, hop
    from bot import durance

    m = [t for t in durance_movers(bot) if math.dist(t[:2], CENTER) < 2 * NEAR]
    if m:
        c = np.mean([t[:2] for t in m], axis=0) - CENTER
    else:
        c = odo.pos.copy()  # away from the waypoint side = toward it is -pos; "away from threat" unknown: go home
    d = -c / max(np.hypot(*c), 1e-6) * 300
    for _ in range(2):
        before = odo.pos.copy()
        hop(bot, odo, *d)
        if odo.lost:
            odo.relocate(bot.capture.grab(), [before])
    print(f"  evaded {len(m)} movers -> {odo.pos.round().tolist()} (HP {bot.hp:.0f}%)", flush=True)


def durance_movers(bot):
    from bot.nav import movers

    return movers(bot, min_area=600)


def patch_scan(bot) -> None:
    from bot import durance

    raw = durance.scan_warps

    def scan(bot_, odo, g, stop, folder):
        hp0 = bot_.hp or 100
        n = raw(bot_, odo, g, stop, folder)
        if (bot_.hp or 100) < hp0 - durance.SCAN["abort_hp"]:
            evade(bot_, odo)
        return n

    durance.scan_warps = scan


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=3)
    ap.add_argument("--hops", type=int, default=60)
    ap.add_argument("--fresh", action="store_true", help="forget the stored search (map changed)")
    ap.add_argument("--no-merc", action="store_true", help="don't revive a dead merc first (that walks Act 3 for Asheara)")
    ap.add_argument("--toward", choices=sorted(DIRS), help="search that way first (a hint, e.g. nw)")
    ap.add_argument("--dest", default="wp_lost_city", help="waypoint to start from (config ui point)")
    ap.add_argument("--style", default="red", help="automap style there (durance.use_style)")
    ap.add_argument("--areas", default="lost_city", help="comma list of area templates that count as still searching")
    ap.add_argument("--outdoor-any", action="store_true", help="unknown area names with this automap count as searching")
    ap.add_argument("--folder", default="lost_city_auto", help="search state folder under maps/<route>/")
    ap.add_argument("--goal", default="ancient_tunnels", help="area template of the place we're looking for")
    ap.add_argument("--pre", default="", help="dx,dy,n: n blind teleports first, then search from there (the Pit: -340,200,9 "
                                              "from the Outer Cloister through the Monastery Gate into Tamoe Highland)")
    ap.add_argument("--min-w", type=int, default=88, help="tooltip width band (px) worth visiting; Trap Door ~108")
    ap.add_argument("--max-w", type=int, default=128)
    ap.add_argument("--max-h", type=int, default=10_000, help="tooltip height limit (px): one-line labels only (~24)")
    ap.add_argument("--label", default="", help="template (bot/assets/templates) the tooltip must contain, e.g. "
                                               "tt_catacombs_level.png")
    ap.add_argument("--debug-dir", default="", help="save every tooltip the scan sees here (scratch/...)")
    ap.add_argument("--marks", action="store_true", help="also take purple exit marks on the automap (Catacombs); "
                                                       "needs --label, hovered for near the mark")
    ap.add_argument("--dx", type=int, default=120, help="hover grid step (px); Durance used 80 x 60")
    ap.add_argument("--dy", type=int, default=80)
    ap.add_argument("--abort-hp", type=int, default=4, help="HP points lost during a scan that stop it")
    ap.add_argument("--seconds", type=int, default=300, help="exploration time per game")
    ap.add_argument("--frontier-wall", type=float, default=0.3, help="canvas average that counts as a wall")
    ap.add_argument("--buy", choices=["mana", "healing", "mixed"], help="fill empty belt columns at Ormus first "
                                                                       "(the tunnels' mixed: healing + mana for Energy Shield)")
    ap.add_argument("--via", default="", help="learned levels to go down first, folder:here:goal;... "
                                             "(Catacombs 3: cata2_auto:catacombs_2:catacombs_3)")
    ap.add_argument("--look-dir", default="", help="save a half-size frame with the automap hidden at each new stop, "
                                                  "to spot stairs by eye (scratch/...)")
    ap.add_argument("--map-off", action="store_true", help="hide the automap while hovering for labels (Catacombs)")
    ap.add_argument("--void", action="store_true", help="also teleport into open space next to stops (rooms without automap walls)")
    ap.add_argument("--no-scan", action="store_true", help="marks only: no tooltip grid scans at stops")
    ap.add_argument("--rescan-all", action="store_true", help="forget which stops were scanned (after a filter change)")
    args = ap.parse_args()
    SCAN.update(min_w=args.min_w, max_w=args.max_w, max_h=args.max_h, debug_dir=args.debug_dir, dx=args.dx, dy=args.dy,
                abort_hp=args.abort_hp)
    if args.label:
        import cv2

        SCAN["label"] = cv2.imread(str(ROOT / "bot" / "assets" / "templates" / args.label))
    from bot import durance as _d

    _d.FRONTIER_WALL = args.frontier_wall
    _d.VOID["on"] = args.void
    SCAN["map_off"] = args.map_off
    SCAN["look_dir"] = args.look_dir
    _d.DURANCE_HEAL = 60  # exploring: go in at 60 % (Ormus heals missed twice in a row, 2026-11-22 17:14)
    if args.no_scan:
        SCAN.update(dx=10_000, dy=10_000)  # one hover point per stop: effectively no scan
    AREAS[:] = args.areas.split(",")
    OUTDOOR_ANY[0] = args.outdoor_any

    use_style(args.style)
    s = start_session()  # backs up saves
    cfg = s.cfg
    cfg["safety"].update(chicken_hp_pct=35, potion_hp_pct=60)
    patch_scan(None)
    folder = ROOT / "maps" / cfg["game"]["route"] / args.folder
    if args.fresh and folder.exists():
        shutil.move(str(folder), str(folder.with_name(folder.name + "_old")))
    (folder / "thumbs").mkdir(parents=True, exist_ok=True)
    if args.marks:  # the hover label for marks lives in the folder (take_warp reads folder / crop)
        (folder / "warps").mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / "bot" / "assets" / "templates" / args.label, folder / "warps" / "mark_label.png")
        SCAN["marks"] = "warps/mark_label.png"
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    g = StopGraph.load(folder / "graph.json")
    if args.rescan_all:
        for st in g.stops:
            st["scanned"] = False
    try:
        for n in range(args.games):
            result = "error"
            odo = None
            try:
                to_durance2(bot, say=lambda m: print(f"game {n + 1}: {m}", flush=True), dest=args.dest, merc=not args.no_merc,
                            buy_mana=bool(args.buy), fill=args.buy or "mana")
                from bot.town import cast_warcries

                cast_warcries(bot)  # Battle Orders: games 1-7 ran at 345 life without it
                BUFFED[0] = bot.clock()
                bot.sleep(0.5)
                if args.pre:  # a fixed lead-in (same landings every game from the waypoint arrival)
                    from bot.nav import CENTER, TP_SETTLE, frame_lag, in_play

                    for seg in args.pre.split(";"):  # "dx,dy,n;dx,dy,n"
                        pdx, pdy, pn = (int(v) for v in seg.split(","))
                        pdx, pdy = in_play(pdx, pdy)
                        for _ in range(pn):
                            bot.click(int(CENTER[0] + pdx), int(CENTER[1] + pdy), "right", hover=0)
                            bot.sleep(TP_SETTLE + frame_lag(bot) + 0.15)
                    bot.sleep(0.6)
                if args.via:
                    from bot.tasks.andariel import down_a_level

                    for seg in args.via.split(";"):
                        vf, vhere, vgoal = seg.split(":")
                        down_a_level(bot, cfg, vf, vhere, vgoal)
                        print(f"game {n + 1}: down to {vgoal}", flush=True)
                    use_style(args.style)
                    bot.sleep(0.6)
                odo = AutomapOdometer.load(folder, ensure_automap(bot))
                print(f"game {n + 1}: arrival fix {odo.pos.round().tolist()} (resp {odo.resp:.2f})", flush=True)

                def save(odo=odo) -> None:
                    odo.save(folder)
                    g.save(folder / "graph.json")

                bot.deadline = bot.clock() + args.seconds
                result = explore_game(bot, odo, g, folder, max_hops=args.hops, save=save,
                                      here=in_lost_city, goal=args.goal,
                                      pre_scan=lambda: safe_to_scan(bot), rescan=True,
                                      toward=DIRS.get(args.toward))
            except BotError as e:
                print(f"game {n + 1}: {e}", flush=True)
            finally:
                bot.deadline = None
                if odo is not None:
                    odo.save(folder)
                g.save(folder / "graph.json")
                bot.guard(False)
                if bot.observe() != "main_menu":
                    save_and_exit(bot)
            warps = [(i, w["w"], w["dest"]) for i, w in enumerate(g.warps)]
            print(f"game {n + 1}: {result}; {len(g.stops)} stops; warps {warps}", flush=True)
            if any(w.get("dest") not in (None, "none") for w in g.warps):
                print("an exit was taken: check warps/dest_*.png (Ancient Tunnels?)", flush=True)
                break
    finally:
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
