"""Build the YOLO dataset for detector v1 (learned-perception plan, part 1). Classes: chest (+ bonfire with --bonfire).

  nice -n 19 python tools/det_dataset.py [--out datasets/det_v1] [--val 0.15] [--bonfire]

Frames, all from Lower Kurast so every chest and bonfire in them can be labeled:
- fixtures/failures/*_chest_not_found.png: chests from fixtures/det/labels.jsonl (hand labels + reviewed template
  proposals, tools/det_propose.py). Frames never labeled are left out (unknown, not empty).
- fixtures/raw/det/*/<stamp>_{chest,bonfire}.jpg from the bot's live hook (bot/recorder.py DetSaver): the chest box is
  the best template match within 45 px of the proved hover point (dropped if it scores < 0.75); other chests in the
  frame come from template proposals (>= 0.9).
Bonfires (--bonfire, off: 2026-11-11 the rule also boxed the gold orb over the characters, fire-enchanted monsters and
spell sparks in fights; needs reviewed labels first): flame blobs >= 450 px (nav.find_fires' rule) grown to cover the fire pit; in LK the only
other flames are torches (smaller). Not used: sampled frames (their "a3" tag also covers the Durance: braziers,
portal) and monsters (only 7 frames have them all boxed).
Writes images as symlinks, YOLO txt labels, data.yaml and a manifest.json (sources, counts).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from det_label import load  # noqa: E402
from det_propose import find, templates  # noqa: E402

CLASSES = ["chest", "bonfire"]
cv2.setNumThreads(2)  # the bot shares this CPU


def bonfires(frame: np.ndarray) -> list[list[int]]:
    hsv = cv2.cvtColor(frame[:560], cv2.COLOR_BGR2HSV)
    m = cv2.dilate(cv2.inRange(hsv, (5, 120, 200), (35, 255, 255)), np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = map(int, st[i])
        # bigger = a fire wall / burning ground; y < 70 = the orange "Immune to ..." line under a monster's name;
        # tall and narrow = a fire-enchanted monster's flame (a pit's flames are about as wide as tall)
        if a >= 450 and 25 <= w < 200 and h < 200 and y >= 70 and h <= 1.3 * w:
            out.append([max(0, x - w // 4), y, w + w // 2, int(h * 1.6)])
    return out


def refine_chest(gray: np.ndarray, pt, tms) -> list[int] | None:
    x, y = pt
    best = (0.0, None)
    for t in tms:
        th, tw = t.shape
        x0, y0 = max(0, x - 45 - tw), max(0, y - 45 - th)
        win = gray[y0:y + 45 + th, x0:x + 45 + tw]
        if win.shape[0] < th or win.shape[1] < tw:
            continue
        _, s, _, loc = cv2.minMaxLoc(cv2.matchTemplate(win, t, cv2.TM_CCOEFF_NORMED))
        bx, by = x0 + loc[0], y0 + loc[1]
        if s > best[0] and bx - 10 <= x <= bx + tw + 10 and by - 25 <= y <= by + th + 10:
            best = (s, [bx, by, tw, th])
    return best[1] if best[0] >= 0.75 else None


def iou_ok(b, boxes, d=25) -> bool:
    return all(abs(b[0] + b[2] / 2 - (k[0] + k[2] / 2)) > d or abs(b[1] + b[3] / 2 - (k[1] + k[3] / 2)) > d for k in boxes)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "datasets" / "det_v1"))
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--bonfire", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    classes = CLASSES if args.bonfire else CLASSES[:1]
    fire = bonfires if args.bonfire else (lambda frame: [])
    tms = templates()
    items, src = [], {"hand": 0, "proposal": 0, "live_chest": 0, "live_chest_dropped": 0, "live_bonfire": 0}

    for rel, r in load().items():
        if not rel.endswith("_chest_not_found.png"):
            continue
        frame = cv2.imread(str(ROOT / rel))
        chests = [b[1:] for b in r["boxes"] if b[0] == "chest"]
        items.append((ROOT / rel, chests, fire(frame)))
        src["proposal" if r["why"] == "proposal" else "hand"] += 1

    for meta in sorted(glob.glob(str(ROOT / "fixtures" / "raw" / "det" / "*" / "*.json"))):
        m = json.loads(Path(meta).read_text())
        if m["cls"] not in ("chest", "bonfire")[:len(classes)] or m.get("act") not in (3, None):
            continue
        img = Path(meta[:-5] + ".jpg")
        frame = cv2.imread(str(img))
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        chests = []
        if m["cls"] == "chest":
            b = refine_chest(gray, m["point"], tms)
            if b is None:
                src["live_chest_dropped"] += 1
                continue
            chests.append(b)
            src["live_chest"] += 1
        else:
            src["live_bonfire"] += 1
        chests += [h[1:] for h in find(gray, tms, 0.9) if iou_ok(h[1:], chests)]
        items.append((img, chests, fire(frame)))

    random.Random(0).shuffle(items)
    nval = max(1, int(len(items) * args.val))
    counts = {"train": [0, 0, 0], "val": [0, 0, 0]}
    for i, (img, chests, fires) in enumerate(items):
        split = "val" if i < nval else "train"
        name = img.parent.name + "_" + img.name if img.parent.name != "failures" else img.name
        ip, lp = out / "images" / split / name, out / "labels" / split / (Path(name).stem + ".txt")
        ip.parent.mkdir(parents=True, exist_ok=True)
        lp.parent.mkdir(parents=True, exist_ok=True)
        if ip.is_symlink() or ip.exists():
            ip.unlink()
        os.symlink(img, ip)
        h, w = cv2.imread(str(img)).shape[:2] if img.suffix == ".jpg" else (720, 1280)
        lines = [f"{c} {(x + bw / 2) / w:.6f} {(y + bh / 2) / h:.6f} {bw / w:.6f} {bh / h:.6f}"
                 for c, boxes in ((0, chests), (1, fires)) for x, y, bw, bh in boxes]
        lp.write_text("\n".join(lines) + ("\n" if lines else ""))
        counts[split][0] += 1
        counts[split][1] += len(chests)
        counts[split][2] += len(fires)
    (out / "data.yaml").write_text(f"path: {out}\ntrain: images/train\nval: images/val\nnames:\n"
                                   + "".join(f"  {i}: {c}\n" for i, c in enumerate(classes)))
    man = {"sources": src, "frames/chests/bonfires": counts, "templates": len(tms)}
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    print(json.dumps(man))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
