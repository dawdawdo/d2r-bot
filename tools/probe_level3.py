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
