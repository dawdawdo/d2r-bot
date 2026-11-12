"""Hand labels for the object detector (learned-perception plan, part 1).

Labels live in fixtures/det/labels.jsonl (committed): one line per frame,
  {"frame": "fixtures/failures/<ts>_chest_not_found.png", "expect": [x, y], "boxes": [["chest", x, y, w, h], ...],
   "why": "monster_on_chest", "note": "..."}
Boxes are in full-frame pixels (1280x720). An empty "boxes" list is a real answer (nothing of interest visible).

  python tools/det_label.py todo chest_not_found [-n 6] [--seed 1]   # next unlabeled frames -> one gridded mosaic
  python tools/det_label.py add <frame> --box chest,465,245,38,37 [--box ...] --why monster_on_chest [--note ...]
  python tools/det_label.py stats
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import re
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "fixtures" / "det" / "labels.jsonl"
CLASSES = ["chest", "chest_open", "bonfire", "lk_hut", "town_wp", "lk_wp", "npc", "monster", "mephisto", "corpse"]
CROP = (480, 320)  # full-frame px around the expected point; shown at 2x


def load() -> dict[str, dict]:
    if not LABELS.exists():
        return {}
    return {(r := json.loads(l))["frame"]: r for l in LABELS.read_text().splitlines() if l.strip()}


def expected_points() -> dict[str, tuple[int, int]]:
    """failure frame stamp -> the chest point the bot was looking for, from the bot logs."""
    out = {}
    pat = re.compile(r"saved failure frame (\S+_chest_not_found\.png)\n.*no chest tooltip near \((\d+), (\d+)\)")
    for log in sorted(glob.glob(str(ROOT / "logs" / "bot-*.log"))):
        txt = Path(log).read_text(errors="replace")
        for m in pat.finditer(txt):
            out[m.group(1)] = (int(m.group(2)), int(m.group(3)))
    return out


def crop_origin(pt) -> tuple[int, int]:
    x0 = int(np.clip(pt[0] - CROP[0] // 2, 0, 1280 - CROP[0]))
    y0 = int(np.clip(pt[1] - CROP[1] // 2 - 20, 0, 720 - CROP[1]))
    return x0, y0


def tile(frame: np.ndarray, pt, title: str, boxes=()) -> np.ndarray:
    x0, y0 = crop_origin(pt)
    c = cv2.resize(frame[y0:y0 + CROP[1], x0:x0 + CROP[0]], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    for gx in range((x0 // 20 + 1) * 20, x0 + CROP[0], 20):
        major = gx % 100 == 0
        cv2.line(c, ((gx - x0) * 2, 0), ((gx - x0) * 2, c.shape[0]), (0, 200, 255) if major else (70, 70, 70), 1)
        if major:
            cv2.putText(c, str(gx), ((gx - x0) * 2 + 3, 14), 0, 0.45, (0, 255, 255), 1)
    for gy in range((y0 // 20 + 1) * 20, y0 + CROP[1], 20):
        major = gy % 100 == 0
        cv2.line(c, (0, (gy - y0) * 2), (c.shape[1], (gy - y0) * 2), (0, 200, 255) if major else (70, 70, 70), 1)
        if major:
            cv2.putText(c, str(gy), (3, (gy - y0) * 2 - 3), 0, 0.45, (0, 255, 255), 1)
    cv2.drawMarker(c, ((pt[0] - x0) * 2, (pt[1] - y0) * 2), (255, 0, 255), cv2.MARKER_CROSS, 24, 2)
    for _, bx, by, bw, bh in boxes:
        cv2.rectangle(c, ((bx - x0) * 2, (by - y0) * 2), ((bx + bw - x0) * 2, (by + bh - y0) * 2), (0, 255, 0), 2)
    cv2.rectangle(c, (0, c.shape[0] - 26), (c.shape[1], c.shape[0]), (0, 0, 0), -1)
    cv2.putText(c, title, (6, c.shape[0] - 8), 0, 0.6, (255, 255, 255), 1)
    return c


def mosaic(tiles: list[np.ndarray], cols: int = 2) -> np.ndarray:
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [cv2.hconcat(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    m = cv2.vconcat(rows)
    s = min(1.0, 1600 / m.shape[1])
    return cv2.resize(m, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("todo")
    t.add_argument("kind")
    t.add_argument("-n", type=int, default=6)
    t.add_argument("--seed", type=int, default=1)
    t.add_argument("--out", default=str(ROOT / "scratch" / "det_todo.jpg"))
    a = sub.add_parser("add")
    a.add_argument("frame")
    a.add_argument("--box", action="append", default=[])
    a.add_argument("--why", default="")
    a.add_argument("--note", default="")
    sh = sub.add_parser("show")
    sh.add_argument("frames", nargs="+")
    sh.add_argument("--out", default=str(ROOT / "scratch" / "det_show.jpg"))
    sub.add_parser("stats")
    args = ap.parse_args()

    done = load()
    exp = expected_points()
    if args.cmd == "todo":
        fs = [f for f in sorted(glob.glob(str(ROOT / "fixtures" / "failures" / f"*_{args.kind}.png")))
              if str(Path(f).relative_to(ROOT)) not in done and Path(f).name in exp]
        random.Random(args.seed).shuffle(fs)
        fs = fs[:args.n]
        tiles = []
        for i, f in enumerate(fs):
            pt = exp[Path(f).name]
            x0, y0 = crop_origin(pt)
            tiles.append(tile(cv2.imread(f), pt, f"#{i} {Path(f).name[:15]} exp {pt} crop@{x0},{y0}"))
            print(f"#{i} {Path(f).relative_to(ROOT)} expect={pt}")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(args.out, mosaic(tiles))
        print("mosaic:", args.out)
    elif args.cmd == "show":  # check labels already written
        tiles = []
        for f in args.frames:
            r = done[f]
            pt = r.get("expect") or [b[1] + b[3] // 2 for b in r["boxes"][:1]] + [b[2] + b[4] // 2 for b in r["boxes"][:1]]
            tiles.append(tile(cv2.imread(str(ROOT / f)), pt, f"{Path(f).name[:15]} {r['why']}", r["boxes"]))
        cv2.imwrite(args.out, mosaic(tiles))
        print("mosaic:", args.out)
    elif args.cmd == "add":
        rel = str(Path(args.frame).resolve().relative_to(ROOT)) if Path(args.frame).exists() else args.frame
        boxes = []
        for b in args.box:
            c, *v = b.split(",")
            assert c in CLASSES, f"unknown class {c}"
            boxes.append([c, *map(int, v)])
        done[rel] = {"frame": rel, "expect": list(exp.get(Path(rel).name, [])) or None, "boxes": boxes,
                     "why": args.why, "note": args.note}
        LABELS.parent.mkdir(parents=True, exist_ok=True)
        LABELS.write_text("".join(json.dumps(r) + "\n" for r in sorted(done.values(), key=lambda r: r["frame"])))
        print(f"{rel}: {len(boxes)} boxes ({len(done)} frames labeled)")
    else:
        from collections import Counter
        print(len(done), "frames;", Counter(b[0] for r in done.values() for b in r["boxes"]),
              Counter(r["why"] for r in done.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
