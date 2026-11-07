"""Build the stash count digit shapes (bot/assets/templates/digits/gems_<d>.png) from a Gems tab frame with
known counts. Binary: stroke 255, the rest 0, with a 1 px margin.

  python tools/make_digit_templates.py
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.vision.stack_count import BAND, TEMPLATES, cell_origin  # noqa: E402

FRAME = ROOT / "fixtures" / "stash" / "gems_counts.png"
TRUTH = [[12, 13, 19, 14, 2, 11, 6], [20, 16, 20, 17, 12, 17, 5], [22, 29, 27, 17, 19, 26, 4],
         [62, 59, 57, 52, 58, 53, None], [1, None, 2, 1, 18, 3, 4]]
STROKE = 80  # the dim "1" is 90-180 on the dark slot
BRIGHT = 120  # the other digits are 200+; this keeps the gem pictures apart from them


def main() -> int:
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    gray = cv2.cvtColor(cv2.imread(str(FRAME)), cv2.COLOR_BGR2GRAY)
    shapes: dict[str, list[np.ndarray]] = defaultdict(list)
    for r, row in enumerate(TRUTH):
        for c, n in enumerate(row):
            if n is None:
                continue
            x, y = cell_origin("gems", r, c)
            band = gray[y + BAND["y0"]:y + BAND["y1"], x + BAND["x0"]:x + BAND["x1"]]
            ps = []  # (x, glyph): bright digits at BRIGHT, the dim 1's bars (<= 3 wide) at STROKE
            for thr, max_w in ((BRIGHT, 8), (STROKE, 3)):
                m = (band > thr).astype(np.uint8)
                m[:, -1:] = 0  # the slot's frame
                k, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
                for i in range(1, k):
                    sx, sy, sw, sh = (int(v) for v in st[i][:4])
                    if 7 <= sh <= 9 and sw <= max_w and sx > 0 and all(abs(sx - p[0]) > 1 for p in ps):
                        ps.append((sx, (lab[sy:sy + sh, sx:sx + sw] == i).astype(np.uint8) * 255))
            ps.sort(key=lambda p: p[0])
            digits = str(n)
            if len(ps) < len(digits):
                print("skip", r, c, n)
                continue
            for d, (_, glyph) in zip(digits, ps[-len(digits):]):
                shapes[d].append(np.pad(glyph, 1))
    for d in "0123456789":
        if not shapes[d]:
            print("MISSING", d)
            continue
        size = Counter(s.shape for s in shapes[d]).most_common(1)[0][0]
        same = [s for s in shapes[d] if s.shape == size]
        vote = (np.mean(same, axis=0) >= 128).astype(np.uint8) * 255
        cv2.imwrite(str(TEMPLATES / f"gems_{d}.png"), vote)
        print(d, size, len(same), "of", len(shapes[d]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
