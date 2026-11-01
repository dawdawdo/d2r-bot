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
    """Hover a grid; where the top-centre name bar changes, save it with the point."""
    x0, y0, w, h = NAME_BAR
    bot.input.move(1270, 590)
    bot.kill.sleep(0.2)
    base = cv2.cvtColor(bot.capture.grab()[y0 : y0 + h, x0 : x0 + w], cv2.COLOR_BGR2GRAY)
    n = 0
    for y in range(60, 560, step):
        for x in range(80, 1200, step):
            bot.check()
            bot.input.move(x, y)
            bot.kill.sleep(0.07)
            f = bot.capture.grab()
            bar = f[y0 : y0 + h, x0 : x0 + w]
            if (cv2.absdiff(cv2.cvtColor(bar, cv2.COLOR_BGR2GRAY), base) > 40).mean() > 0.03:
                cv2.imwrite(str(out / f"name_{x}_{y}.png"), bar)
                n += 1
    bot.input.move(1270, 590)
    print(f"name scan: {n} hovers showed a name bar", flush=True)


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


def back_to(bot, ref, max_hops: int = 5, tol: float = 70, min_resp: float = 0.2) -> bool:
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
        if resp < 0.08:  # no idea where she is: hop toward the far side of the moat as recorded
            dx, dy = 430, -50
        else:
            scale = min(1.0, 450 / max(dist / WORLD_PER_PX, 1))
            dx, dy = -off[0] / WORLD_PER_PX * scale, -off[1] / WORLD_PER_PX * scale
        bot.click(int(640 + dx), int(330 + dy), "right", hover=0)
        bot.sleep(0.45)
    return False


CLEAR_SPOTS = [(780, 250), (520, 260), (720, 400)]  # Blizzard targets around her: upper right first (packs come from there)


def names_near(bot, radius: int = 330, n: int = 20) -> list[tuple[int, int]]:
    """Hover a ring + inner ring around her; the points where a monster name bar shows."""
    x0, y0, w, h = NAME_BAR
    bot.input.move(1270, 590)
    bot.kill.sleep(0.15)
    base = cv2.cvtColor(bot.capture.grab()[y0 : y0 + h, x0 : x0 + w], cv2.COLOR_BGR2GRAY)
    hits = []
    for r, k in ((radius, n), (radius // 2, n // 2)):
        for j in range(k):
            a = 2 * np.pi * j / k
            x, y = int(640 + r * np.cos(a)), int(330 + 0.6 * r * np.sin(a))
            if not (60 < y < 560):
                continue
            bot.check()
            bot.input.move(x, y)
            bot.kill.sleep(0.06)
            bar = cv2.cvtColor(bot.capture.grab()[y0 : y0 + h, x0 : x0 + w], cv2.COLOR_BGR2GRAY)
            if (cv2.absdiff(bar, base) > 40).mean() > 0.03:
                hits.append((x, y))
    bot.input.move(1270, 590)
    return hits


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
    args = ap.parse_args()
    def token(h: str):
        if h.startswith("w"):
            return float(h[1:])
        if h in ("R", "D", "C"):  # R: remember this spot; D: teleport back to it by the view
            return h
        if h[0] in "bos":  # b/o/s x,y,n: n Blizzards / Frozen Orbs / Static Fields at screen (x, y)
            return (h[0],) + tuple(int(v) for v in h[1:].split(","))
        return tuple(int(v) for v in h.split(","))

    hops = [token(h) for h in args.hops.split()]

    s = start_session()  # backs up saves
    cfg = s.cfg
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
        to_durance2(bot, say=print)
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
            if h == "R":
                ref = bot.capture.grab()
                cv2.imwrite(str(out / f"{i:02d}_ref.png"), ref)
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
                continue
            if isinstance(h[0], str):
                cast(bot, *h, out, i)
                continue
            dx, dy = h
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
