"""Go to a world point of a learned dungeon map and look closely (frames + a dense tooltip scan).

  python tools/cata_goto.py --folder cata2_auto --to -3568,1096 [--dest wp_catacombs_2] [--style tunnel]

New Hell game -> waypoint -> automap odometer from maps/<route>/<folder> -> follow the stop graph to the stop nearest
the point, then hop to it -> scratch/goto/: frames with the automap on and off, every tooltip under a 40 x 30 px
hover grid -> ALWAYS save & exit. For finding a level exit the finder's coarse scan missed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import durance  # noqa: E402
from bot.config import ROOT  # noqa: E402
from bot.controller import BotError, Controller  # noqa: E402
from bot.io import open_backend  # noqa: E402
from bot.lifecycle import save_and_exit  # noqa: E402
from bot.session import start_session  # noqa: E402
from bot.vision.screen import ScreenClassifier  # noqa: E402
from bot.vision.tooltip import find_tooltip  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--to", default="", help="world x,y (px from the waypoint arrival)")
    ap.add_argument("--dest", default="wp_catacombs_2")
    ap.add_argument("--style", default="tunnel")
    ap.add_argument("--out", default="goto")
    ap.add_argument("--no-scan", action="store_true", help="frames only (several --to points: x,y;x,y)")
    ap.add_argument("--label", default="tt_catacombs_level.png", help="keep only tooltips containing this ('' = all)")
    ap.add_argument("--step", default="60,45", help="hover grid step x,y (px)")
    ap.add_argument("--map-off", action="store_true", help="hide the automap while scanning")
    ap.add_argument("--look", action="store_true", help="also save a frame with the automap hidden at each point")
    ap.add_argument("--targets", default="", help="json file of [x, y] points (instead of --to)")
    ap.add_argument("--first", type=int, default=0, help="index of the first point to visit in --targets")
    ap.add_argument("--count", type=int, default=1000)
    args = ap.parse_args()
    args.step = [int(v) for v in args.step.split(",")]
    label = cv2.imread(str(ROOT / "bot" / "assets" / "templates" / args.label)) if args.label else None
    if args.targets:
        import json

        targets = json.loads(Path(args.targets).read_text())[args.first : args.first + args.count]
    else:
        targets = [[float(v) for v in t.split(",")] for t in args.to.split(";")]
    out = ROOT / "scratch" / args.out
    out.mkdir(parents=True, exist_ok=True)
    durance.use_style(args.style)
    s = start_session()
    cfg = s.cfg
    cfg["safety"].update(chicken_hp_pct=35, potion_hp_pct=60)
    folder = ROOT / "maps" / cfg["game"]["route"] / args.folder
    b = open_backend(cfg["game"]["window_title"], launch_exe=cfg["game"]["exe"])
    bot = Controller(b.window, b.capture, b.input, ScreenClassifier.from_config(cfg["vision"]["states"]),
                     s.kill, cfg)
    b.window.focus()
    try:
        durance.to_durance2(bot, say=lambda m: print(m, flush=True), dest=args.dest, merc=True)
        from bot.town import cast_warcries

        cast_warcries(bot)
        bot.sleep(0.5)
        odo = durance.AutomapOdometer.load(folder, durance.ensure_automap(bot))
        g = durance.StopGraph.load(folder / "graph.json")
        w = durance.Walker(bot, odo, g, folder, scan=False)
        for k, target in enumerate(targets):
            near = g.nearest(target, within=1e9)
            print(f"arrival {odo.pos.round().tolist()} resp {odo.resp:.2f}; stop {near} at "
                  f"{[round(v) for v in g.stops[near]['pos']]}", flush=True)
            w.travel(near)
            w.go(target, tol=120, max_hops=6)
            print(f"at {odo.pos.round().tolist()} (target {target}) HP {bot.hp or 0:.0f}%", flush=True)
            cv2.imwrite(str(out / f"map_on{k if k else ''}.png"), bot.capture.grab())
            if args.look:  # the scene without the automap, to look at by eye; map back on for the odometer
                bot.press("tab")
                bot.kill.sleep(0.45)
                cv2.imwrite(str(out / f"look_{args.first + k:03d}_{round(odo.pos[0])}_{round(odo.pos[1])}.png"),
                            bot.capture.grab())
                durance.ensure_automap(bot)
            if args.no_scan:
                continue
            if args.map_off:
                bot.press("tab")
                bot.kill.sleep(0.4)
                cv2.imwrite(str(out / f"map_off{k if k else ''}.png"), bot.capture.grab())
            n = 0
            for y in range(70, 560, args.step[1]):
                for x in range(100, 1180, args.step[0]):
                    bot.input.move(x, y)
                    bot.kill.sleep(0.07)
                    f = bot.capture.grab()
                    box = find_tooltip(f, x, y, half_w=230, max_w=420)
                    if box is not None and box[2] >= 60 and box[3] <= 34 and (label is None or durance._has_label(f, box, label)):
                        bx, by, bw, bh = box
                        cv2.imwrite(str(out / f"tt{k}_{x}_{y}_w{bw}_h{bh}.png"), f[by : by + bh, bx : bx + bw])
                        print(f"  label at ({x}, {y}) {bw}x{bh} -> world {[round(odo.pos[0] + x - 640), round(odo.pos[1] + y - 330)]}",
                              flush=True)
                        n += 1
                bot.check()
            print(f"target {k}: {n} labels", flush=True)
            if args.map_off:
                bot.press("tab")
                bot.kill.sleep(0.4)
        print(f"frames in {out}", flush=True)
    except BotError as e:
        print(f"error: {e}", flush=True)
    finally:
        bot.guard(False)
        if bot.observe() != "main_menu":
            save_and_exit(bot)
        bot.release_all()
        s.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
