"""Look around Durance of Hate Level 3: bot route down the stairs, then teleports in given directions.

  python tools/probe_level3.py --hops "300,-150 300,-150 0,-200"   # screen px from her, per teleport

Each landing: a half-size frame and the automap fix on a Level 3 canvas (maps/<route>/durance3_auto/,
grown across runs) go to durance3_auto/probe/<n>/. Then save & exit. For mapping the way to Mephisto.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.durance import AutomapOdometer, StopGraph, ensure_automap, level_now, to_durance2, to_level3  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.nav import hop  # noqa: E402
from bot import state  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.town import set_players  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402


NAME_BAR = (440, 0, 400, 60)  # a hovered monster's name and life bar, top centre


def scan_names(bot, out: Path, step: int = 70) -> None:
    """Hover a grid; save the frame (and what name_bar reads) wherever a name bar shows, plus every
    25th hover as a control."""
    from bot.vision.namebar import name_bar

    n = k = 0
    for y in range(60, 560, step):
        for x in range(80, 1200, step):
            bot.check()
            bot.input.move(x, y)
            bot.kill.sleep(0.12)
            f = bot.capture.grab()
            nb = name_bar(f)
            k += 1
            if nb is not None or k % 25 == 0:
                tag = "hit" if nb else "ctl"
                cv2.imwrite(str(out / f"scan_{tag}_{x}_{y}.jpg"), f)
                if nb:
                    n += 1
                    print(f"name bar at ({x}, {y}): {nb}", flush=True)
    bot.input.move(1270, 590)
    print(f"name scan: {n} of {k} hovers showed a name bar", flush=True)


SPELLS = {"b": "blizzard", "o": "frozen_orb", "s": "static_field"}


def cast(bot, kind: str, x: int, y: int, n: int, out: Path, i: int) -> None:
    """n casts of a spell at (x, y); the name bar (top centre: life of whatever's under the cursor)
    is saved after each."""
    sk = bot.cfg["hotkeys"]["skills"]
    bot.press(sk[SPELLS[kind]])
    try:
        for k in range(n):
            bot.click(x, y, "right", hover=0)
            bot.sleep(0.5)
            x0, y0, w, h = NAME_BAR
            f = bot.capture.grab()
            cv2.imwrite(str(out / f"{i:02d}_{kind}{k:02d}_bar.png"), f[y0 : y0 + h, x0 : x0 + w])
            if k % 4 == 3:
                cv2.imwrite(str(out / f"{i:02d}_{kind}{k:02d}.jpg"), cv2.resize(f, (640, 360)))
            print(f"{kind} {k}: HP {bot.hp} MP {bot.mp}", flush=True)
    finally:
        bot.press(sk["teleport"])


WORLD_PER_PX = 1.1  # odometer world px per screen px of a teleport (Level 3 hops, 2026-11-01)


SINCE_REF: list = []  # screen-px hops made since the spot was remembered (R): reversed when the view is no help


def back_to(bot, ref, max_hops: int = 5, tol: float = 90, min_resp: float = 0.15) -> bool:
    """Teleport until this view matches `ref` (the spot remembered with R): view_offset says how far
    she is from it; hop the other way. True once within `tol` world px."""
    from bot.durance import view_offset

    for k in range(max_hops + 1):
        off, resp = view_offset(ref, bot.capture.grab())
        dist = float(np.hypot(*off))
        print(f"back: off {off.round().tolist()} resp {resp:.2f} (hop {k})", flush=True)
        if resp >= min_resp and dist <= tol:
            return True
        if k == max_hops:
            break
        if resp < 0.08:  # the view is no help: undo the hops made since R (one hop's worth at a time)
            back = -np.sum(SINCE_REF, axis=0) if SINCE_REF else np.array([430.0, -50.0])
            n = max(1, int(np.ceil(np.hypot(*back) / 420)))
            dx, dy = back / n
            if SINCE_REF:
                SINCE_REF.append((dx, dy))  # count it, so the rest of the way stays right
        else:
            scale = min(1.0, 450 / max(dist / WORLD_PER_PX, 1))
            dx, dy = -off[0] / WORLD_PER_PX * scale, -off[1] / WORLD_PER_PX * scale
        bot.click(int(640 + dx), int(330 + dy), "right", hover=0)
        bot.sleep(0.45)
    return False


CLEAR_SPOTS = [(780, 250), (520, 260), (720, 400)]  # Blizzard targets around her: upper right first (packs come from there)


def names_near(bot, radius: int = 330, n: int = 20) -> list[tuple[int, int]]:
    """Hover a ring + inner ring around her; the points where a monster's name bar shows."""
    from bot.vision.namebar import name_bar

    hits = []
    for r, k in ((radius, n), (radius // 2, n // 2)):
        for j in range(k):
            a = 2 * np.pi * j / k
            x, y = int(640 + r * np.cos(a)), int(330 + 0.6 * r * np.sin(a))
            if not (60 < y < 560):
                continue
            bot.check()
            bot.input.move(x, y)
            bot.kill.sleep(0.07)
            if name_bar(bot.capture.grab()) is not None:
                hits.append((x, y))
    bot.input.move(1270, 590)
    return hits


MEPH_GRID = sorted([(x, y) for y in range(20, 430, 55) for x in range(80, 1200, 80)],
                   key=lambda p: (p[0] - 720) ** 2 + 4 * (p[1] - 50) ** 2)  # his moat-edge spot first (top centre)
# Council hunt: top band first (Wyand Voidbringer, Mana Burn, stands up-right of the dock), then the rest
HUNT_GRID = sorted([(x, y) for y in range(60, 520, 70) for x in range(100, 1200, 90)],
                   key=lambda p: (p[1] > 200, abs(p[0] - 760)))


def first_name(bot, pts, dwell: float = 0.06):
    """Hover pts in order; the first (point, bar) where a name bar shows."""
    from bot.vision.namebar import name_bar

    for x, y in pts:
        bot.check()
        bot.input.move(x, y)
        bot.kill.sleep(dwell)
        nb = name_bar(bot.capture.grab())
        if nb is not None:
            return (x, y), nb
    return None


def hunt_here(bot, ref, out: Path, i: int, limit: float = 60, min_mp: float = 30) -> bool:
    """Kill what's near the spot: find a name bar, Blizzard it until its bar is gone, again, until a full
    scan finds none (True). Mephisto is left alone (the moat trick handles him)."""
    from bot.durance import view_offset
    from bot.vision.namebar import name_bar

    sk = bot.cfg["hotkeys"]["skills"]
    t0, rnd = time.time(), 0
    try:
        while time.time() - t0 < limit:
            off, resp = view_offset(ref, bot.capture.grab())
            if resp < 0.1 or float(np.hypot(*off)) > 150:
                print(f"hunt: off the spot ({off.round().tolist()}, resp {resp:.2f}) -> back", flush=True)
                if not back_to(bot, ref):
                    raise BotError("pushed off the spot")
            if (bot.mp or 0) < min_mp:
                bot.sleep(0.3)
                continue
            rnd += 1
            hit = first_name(bot, HUNT_GRID)
            if hit is None:
                print(f"hunt round {rnd}: no names HP {bot.hp} MP {bot.mp}", flush=True)
                bot.input.move(1270, 590)
                return True
            (x, y), nb = hit
            if nb["mephisto"]:
                print(f"hunt round {rnd}: Mephisto at ({x}, {y}) life {nb['life']:.2f}: leaving him", flush=True)
                bot.input.move(1270, 590)
                return True
            bot.press(sk["blizzard"])
            for k in range(3):
                bot.click(x, y, "right", hover=0)
                bot.sleep(0.5)
            bot.press(sk["teleport"])
            now = name_bar(bot.capture.grab())
            print(f"hunt round {rnd}: name at ({x}, {y}) life {nb['life']:.2f} -> "
                  f"{'gone' if now is None else round(now['life'], 2)} HP {bot.hp} MP {bot.mp}", flush=True)
            if rnd % 2 == 1:
                cv2.imwrite(str(out / f"{i:02d}_hunt{rnd:02d}.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
    finally:
        bot.press(sk["teleport"])
    return False


def find_meph(bot, last=None) -> tuple[tuple[int, int], float] | None:
    """Hover his last spot, then a grid over the left half: (point, life) where Mephisto's bar shows."""
    from bot.vision.namebar import name_bar

    if last:  # seen before: only near his last point (a full grid = 11 s standing in his lightning)
        lx, ly = last
        pts = [(min(1260, max(20, lx + dx)), min(560, max(8, ly + dy)))
               for dy in (0, 25, -12, 50) for dx in (0, -40, 40, -80, 80)]
    else:
        pts = MEPH_GRID
    for x, y in pts:
        bot.check()
        bot.input.move(x, y)
        bot.kill.sleep(0.1)
        nb = name_bar(bot.capture.grab())
        if nb and nb["mephisto"]:
            return (x, y), nb["life"]
    return None


WAKE = [(720, 30), (560, 40), (880, 40)]
RETREAT = (100, 180)  # screen px: down-right, away from his moat-edge spot (top centre)
RETREAT_WAIT = 1.5
FLINCH_HP = 85  # life %% that cuts a volley short (bursts of 400+ life in ~2 s, 2026-11-01)


def kill_meph(bot, ref, out: Path, i: int, limit: float = 180, min_mp: float = 40) -> bool:
    """Blizzard Mephisto from here until his bar has been low and he can't be found (True)."""
    from bot.durance import view_offset
    from bot.vision.namebar import name_bar

    sk = bot.cfg["hotkeys"]["skills"]
    t0, last, low, misses, rnd = time.time(), None, 1.0, 0, 0
    try:
        while time.time() - t0 < limit:
            # first the spot: "teleport when struck" (her gear) throws her around, mid-wait too
            off, resp = view_offset(ref, bot.capture.grab())
            if resp < 0.1 or float(np.hypot(*off)) > 150:  # resp 0.12-0.3 on the dock itself
                print(f"kill: off the spot ({off.round().tolist()}, resp {resp:.2f}) -> back", flush=True)
                if not back_to(bot, ref):
                    raise BotError("pushed off the spot")
            if (bot.mp or 0) < min_mp:
                bot.sleep(0.3)
                continue
            rnd += 1
            cv2.imwrite(str(out / f"{i:02d}_round{rnd:02d}.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
            found = find_meph(bot, last)
            if found is None:
                misses += 1
                print(f"kill round {rnd}: Mephisto not found (low {low:.2f}, misses {misses})", flush=True)
                if low < 0.3 and misses >= 3:
                    return True
                if last is not None and RETREAT:  # seen before: look again from a safe distance first
                    SINCE_REF.clear()
                    SINCE_REF.append(RETREAT)
                    bot.click(640 + RETREAT[0], 330 + RETREAT[1], "right", hover=0)
                    bot.sleep(RETREAT_WAIT)
                    if not back_to(bot, ref):
                        raise BotError("couldn't get back after the retreat")
                    if misses >= 4:
                        last = None  # he walked off: full search next time
                if low >= 1.0 and misses % 2 == 0:  # never seen: wake him on his platform (top centre
                    # from Stephen's spot, his Blizzards at (708-729, 8-45) in views 202-214)
                    wx, wy = WAKE[(misses // 2) % len(WAKE)]
                    print(f"kill: waking him at ({wx}, {wy})", flush=True)
                    bot.press(sk["blizzard"])
                    for _ in range(2):
                        bot.click(wx, wy, "right", hover=0)
                        bot.sleep(0.5)
                        nb = name_bar(bot.capture.grab())
                        if nb and nb["mephisto"]:  # he walked under the cursor: that's his spot
                            last, low = (wx, wy), min(low, nb["life"])
                            print(f"kill: Mephisto under the wake point, life {nb['life']:.2f}", flush=True)
                            break
                    bot.press(sk["teleport"])
                bot.sleep(0.8)
                continue
            misses, (last, life) = 0, found
            low = min(low, life)
            bot.press(sk["blizzard"])
            hit = False
            for k in range(3):
                bot.click(*last, "right", hover=0)
                bot.sleep(0.5)
                nb = name_bar(bot.capture.grab())
                if nb and nb["mephisto"]:
                    low = min(low, nb["life"])
                if (bot.hp or 100) < FLINCH_HP:  # his lightning found her: out now, not after the volley
                    hit = True
                    break
            bot.press(sk["teleport"])
            print(f"kill round {rnd}: Mephisto at {last} life {life:.2f} (low {low:.2f}) HP {bot.hp} MP {bot.mp}",
                  flush=True)
            if RETREAT:  # hit and run: his lightning took 520 -> 42 life in < 2 s here (2026-11-01 18:17)
                SINCE_REF.clear()
                SINCE_REF.append(RETREAT)  # so a weak view match falls back to undoing the retreat
                bot.click(640 + RETREAT[0], 330 + RETREAT[1], "right", hover=0)
                bot.sleep(RETREAT_WAIT * (2 if hit else 1))  # the Blizzard keeps falling on him meanwhile
                if not back_to(bot, ref):
                    raise BotError("couldn't get back after the retreat")
    finally:
        bot.press(sk["teleport"])
    return False


def clear_here(bot, out: Path, i: int, limit: float = 45, min_mp: float = 50) -> bool:
    """Blizzard around her until a hover sweep finds no monster name (True) or `limit` s pass."""
    sk = bot.cfg["hotkeys"]["skills"]
    t0, rnd, targets = time.time(), 0, list(CLEAR_SPOTS)
    try:
        while time.time() - t0 < limit:
            while (bot.mp or 0) < min_mp and time.time() - t0 < limit:
                bot.sleep(0.3)  # the guard drinks / chickens meanwhile
            bot.press(sk["blizzard"])
            for x, y in targets[:3]:
                bot.click(x, y, "right", hover=0)
                bot.sleep(0.45)
            bot.press(sk["teleport"])
            bot.sleep(0.6)
            hits = names_near(bot)
            rnd += 1
            print(f"clear round {rnd}: {len(hits)} name hovers {hits[:4]} HP {bot.hp} MP {bot.mp}", flush=True)
            cv2.imwrite(str(out / f"{i:02d}_clear{rnd:02d}.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
            if not hits:
                return True
            # aim at what's there: the hits' centre first, then the default spots
            cx, cy = np.mean(hits, axis=0).astype(int)
            targets = [(int(cx), int(cy))] + list(CLEAR_SPOTS)
    finally:
        bot.press(sk["teleport"])
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hops", default="", help='"dx,dy dx,dy w2 ..." screen px per teleport; wN = wait N s')
    ap.add_argument("--watch", type=float, default=0, help="then stand and save a full frame per second")
    ap.add_argument("--scan", action="store_true", help="then hover a grid; save monster name bars")
    ap.add_argument("--players", type=int, help="/players N on arrival in Durance 2 (LK batches reset theirs)")
    ap.add_argument("--buy-mana", action="store_true", help="fill the belt with Ormus's mana potions first")
    ap.add_argument("--es-hp", type=float, help="shield-broken chicken below this life %% (config: 75; 0 = off)")
    args = ap.parse_args()
    def token(h: str):
        if h.startswith("w"):
            return float(h[1:])
        if h.startswith("L"):  # L206: Stephen's recorded view 206 becomes the spot to return to
            return h
        if h in ("R", "D", "C", "M", "H", "B"):  # R: remember this spot; D: teleport back to it by the view
            return h
        if h[0] in "bos":  # b/o/s x,y,n: n Blizzards / Frozen Orbs / Static Fields at screen (x, y)
            return (h[0],) + tuple(int(v) for v in h[1:].split(","))
        return tuple(int(v) for v in h.split(","))

    hops = [token(h) for h in args.hops.split()]

    s = start_session()  # backs up saves
    cfg = s.cfg
    if args.buy_mana:
        cfg["safety"]["potion_hp_pct"] = 0  # mana potions don't heal life: drink them for mana only
        cfg["safety"]["potion_mp_pct"] = 50  # keep the shield up: his lightning empties mana fast
    if args.es_hp is not None:
        cfg["safety"]["es_broken_hp_pct"] = args.es_hp
    maps = ROOT / "maps" / cfg["game"]["route"]
    auto2, auto3 = maps / "durance2_auto", maps / "durance3_auto"
    out = auto3 / "probe" / time.strftime("%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    log = []
    try:
        to_durance2(bot, say=print, buy_mana=args.buy_mana)
        if args.players:
            set_players(bot, args.players)
            st = state.load()
            st.pop("players_window", None)  # the next LK batch sets its own /players again
            state.save(st)
        bot.sleep(2.0)
        odo = AutomapOdometer.load(auto2, ensure_automap(bot))
        to_level3(bot, odo, StopGraph.load(auto2 / "graph.json"), None, auto2)
        bot.sleep(1.0)
        if level_now(bot) != 3:
            raise BotError("not on Level 3")
        f = bot.capture.grab()
        odo3 = AutomapOdometer.load(auto3, f)
        cv2.imwrite(str(out / "arrival.jpg"), cv2.resize(f, (640, 360)))
        print(f"arrival fix {odo3.pos.round().tolist()} resp {odo3.resp:.2f}", flush=True)
        log.append({"i": -1, "pos": odo3.pos.round(1).tolist(), "resp": round(float(odo3.resp), 3)})
        for i, h in enumerate(hops):
            if isinstance(h, float):
                bot.sleep(h)
                continue
            if isinstance(h, str) and h.startswith("L"):
                ref = cv2.imread(str(maps / "durance3_route" / "views" / f"{int(h[1:]):03d}.jpg"))
                continue
            if h == "R":
                SINCE_REF.clear()
                ref = bot.capture.grab()
                cv2.imwrite(str(out / f"{i:02d}_ref.png"), ref)
                continue
            if h == "B":  # recast Energy Shield + Frozen Armor here (town buffs may have run out)
                from bot.town import cast_buffs

                cast_buffs(bot)
                print(f"buffs recast: HP {bot.hp} MP {bot.mp}", flush=True)
                continue
            if h == "H":
                print(f"hunt: {hunt_here(bot, ref, out, i)}", flush=True)
                continue
            if h == "M":
                print(f"kill: {kill_meph(bot, ref, out, i)}", flush=True)
                cv2.imwrite(str(out / f"{i:02d}_after_kill.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
                continue
            if h == "C":
                print(f"clear: {clear_here(bot, out, i)}", flush=True)
                continue
            if h == "D":
                ok = back_to(bot, ref)
                cv2.imwrite(str(out / f"{i:02d}_back.jpg"), cv2.resize(bot.capture.grab(), (640, 360)))
                print(f"back to the spot: {ok} HP {bot.hp} MP {bot.mp}", flush=True)
                if not ok:
                    raise BotError("couldn't get back to the remembered spot")
                SINCE_REF.clear()  # hops from here on are relative to this spot
                continue
            if isinstance(h[0], str):
                cast(bot, *h, out, i)
                continue
            dx, dy = h
            SINCE_REF.append((dx, dy))
            hop(bot, odo3, dx, dy)
            f = bot.capture.grab()
            cv2.imwrite(str(out / f"{i:02d}.jpg"), cv2.resize(f, (640, 360)))
            rec = {"i": i, "hop": [dx, dy], "pos": odo3.pos.round(1).tolist(), "resp": round(float(odo3.resp), 3),
                   "lost": bool(odo3.lost), "hp": bot.hp, "mp": bot.mp}
            log.append(rec)
            print(rec, flush=True)
        for k in range(int(args.watch)):
            bot.sleep(1.0)  # the guard drinks / chickens meanwhile
            cv2.imwrite(str(out / f"watch_{k:02d}.png"), bot.capture.grab())
            print(f"watch {k}: HP {bot.hp} MP {bot.mp}", flush=True)
        if args.scan:
            scan_names(bot, out)
        odo3.save(auto3)
    except BotError as e:
        print(f"stopped: {e}", flush=True)
    finally:
        (out / "log.json").write_text(json.dumps(log, indent=1))
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    print(f"-> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
