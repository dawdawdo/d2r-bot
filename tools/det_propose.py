"""Chest proposals for review: template-match the hand-labeled chests (fixtures/det/labels.jsonl) over unlabeled frames.

  python tools/det_propose.py run 'fixtures/failures/*_chest_not_found.png' [--thr 0.9]   # -> scratch/det_props.json
  python tools/det_propose.py sheet [--page 0]      # numbered crops, 16 per sheet -> scratch/det_props_<page>.jpg
  python tools/det_propose.py accept --reject 3,17  # every proposal except the rejected -> labels.jsonl (why=proposal)

Leave-one-out on the first 34 hand labels (2026-11-11): visible chests score 0.89-1.00, frames without one <= 0.87.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from det_label import LABELS, load  # noqa: E402

PROPS = ROOT / "scratch" / "det_props.json"


def templates() -> list[np.ndarray]:
    out = []
    for r in load().values():
        if r["why"] == "proposal":  # hand labels only: 16 templates, not hundreds
            continue
        im = None
        for c, x, y, w, h in r["boxes"]:
            if c == "chest":
                im = cv2.imread(str(ROOT / r["frame"]), cv2.IMREAD_GRAYSCALE) if im is None else im
                out.append(im[y:y + h, x:x + w])
    return out


def find(gray: np.ndarray, tms, thr: float) -> list[list]:
    hits = []
    for t in tms:
        res = cv2.matchTemplate(gray[:560], t, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= thr)
        hits += [(float(res[y, x]), int(x), int(y), t.shape[1], t.shape[0]) for y, x in zip(ys, xs)]
    hits.sort(reverse=True)
    keep = []
    for s, x, y, w, h in hits:  # greedy NMS on centers
        if all(abs(x + w / 2 - (k[1] + k[3] / 2)) > 25 or abs(y + h / 2 - (k[2] + k[4] / 2)) > 25 for k in keep):
            keep.append([round(s, 3), x, y, w, h])
    return keep


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("pattern")
    r.add_argument("--thr", type=float, default=0.9)
    s = sub.add_parser("sheet")
    s.add_argument("--page", type=int, default=0)
    a = sub.add_parser("accept")
    a.add_argument("--reject", default="")
    args = ap.parse_args()

    if args.cmd == "run":
        tms, done = templates(), load()
        props = []
        for f in sorted(glob.glob(str(ROOT / args.pattern))):
            rel = str(Path(f).relative_to(ROOT))
            if rel in done:
                continue
            for hit in find(cv2.imread(f, cv2.IMREAD_GRAYSCALE), tms, args.thr):
                props.append({"frame": rel, "score": hit[0], "box": hit[1:]})
        PROPS.write_text(json.dumps(props))
        print(f"{len(props)} proposals in {len({p['frame'] for p in props})} frames ({len(tms)} templates)")
    elif args.cmd == "sheet":
        props = json.loads(PROPS.read_text())
        page = props[args.page * 16:(args.page + 1) * 16]
        tiles = []
        for i, p in enumerate(page, args.page * 16):
            im = cv2.imread(str(ROOT / p["frame"]))
            x, y, w, h = p["box"]
            cx, cy = x + w // 2, y + h // 2
            x0, y0 = int(np.clip(cx - 80, 0, 1120)), int(np.clip(cy - 60, 0, 600))
            c = im[y0:y0 + 120, x0:x0 + 160].copy()
            cv2.rectangle(c, (x - x0, y - y0), (x - x0 + w, y - y0 + h), (0, 255, 0), 1)
            c = cv2.resize(c, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            cv2.putText(c, f"#{i} {p['score']:.2f}", (4, 20), 0, 0.6, (0, 255, 255), 2)
            tiles.append(c)
        while len(tiles) % 4:
            tiles.append(np.zeros_like(tiles[0]))
        out = ROOT / "scratch" / f"det_props_{args.page}.jpg"
        cv2.imwrite(str(out), cv2.vconcat([cv2.hconcat(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]))
        print(out, f"({len(props)} proposals, {(len(props) + 15) // 16} sheets)")
    else:
        props = json.loads(PROPS.read_text())
        bad = {int(v) for v in args.reject.split(",") if v.strip()}
        done = load()
        n = 0
        for i, p in enumerate(props):
            if i in bad:
                continue
            r = done.setdefault(p["frame"], {"frame": p["frame"], "expect": None, "boxes": [], "why": "proposal",
                                             "note": "template proposal, reviewed; monsters not boxed"})
            r["boxes"].append(["chest", *p["box"]])
            n += 1
        LABELS.write_text("".join(json.dumps(r) + "\n" for r in sorted(done.values(), key=lambda r: r["frame"])))
        print(f"accepted {n}, rejected {len(bad)}; {len(done)} frames labeled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
