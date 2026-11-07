"""Stack counts on the stash's Gems and Runes tabs (D2R stacks: one slot per kind, its count bottom right).

The digits are a thin font, right-aligned against the slot's right edge: white on the dark Gems slots, white on
the light rune stone, except "1", drawn dim (on a rune barely brighter than the stone). One binary shape per
digit (cut from the Gems tab, tools/make_digit_templates.py), matched with normalized correlation, which doesn't
care how bright the background is. Errs low: a rune's faintest 1s get missed (Sol 10 read 0, 2026-11-07: the bar
15 levels over the stone, a carving beside it), which only means cubing less.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates" / "digits"
# slot grids, measured 2026-11-07 at 1280x720: top-left of slot (0,0), pitch, rows x cols
TABS = {
    "gems": {"x0": 64, "y0": 91, "px": 47.0, "py": 38.75, "rows": 5, "cols": 7},
    "runes": {"x0": 46, "y0": 107, "px": 40.1, "py": 40.2, "rows": 5, "cols": 9},
}
# the Runes tab's last two rows are partial: (row, col) of each slot, El..Zod
RUNE_SLOTS = [(r, c) for r in range(3) for c in range(9)] + [(3, 0), (3, 1), (3, 7), (3, 8), (4, 0), (4, 8)]
# Gems tab: columns are colors, rows grades
GEM_COLORS = ["Diamond", "Emerald", "Ruby", "Topaz", "Amethyst", "Sapphire", "Skull"]
GEM_GRADES = ["Chipped", "Flawed", "", "Flawless", "Perfect"]
BAND = {"x0": 12, "x1": 36, "y0": 21, "y1": 35}  # where the count sits, relative to the slot's top-left
MIN_SCORE = 0.55
DIM_ONE_SCORE = 0.65  # "1" is a plain bar: on a rune, the stone's lit edge scores up to 0.57, real ones 0.70
ONE_PENALTY = 0.15  # ...and so do other digits' upright strokes: a "1" must beat them by this much
FAINT_TENS = 0.4  # a tens "1" next to a gem's picture (Topaz 17 matched 0.47), or on a rune (Ral 17: 0.48)
# ...where it's told from the carving by being brighter than the stone on both sides: real 19+, false 10 or less
RUNE_TENS_CONTRAST = 15


def cell_origin(tab: str, r: int, c: int) -> tuple[int, int]:
    t = TABS[tab]
    return int(round(t["x0"] + c * t["px"])), int(round(t["y0"] + r * t["py"]))


def slot_center(tab: str, r: int, c: int) -> tuple[int, int]:
    x, y = cell_origin(tab, r, c)
    return x + 17, y + 17


@lru_cache(maxsize=1)
def _templates() -> dict[str, np.ndarray]:
    out = {}
    for d in "0123456789":
        img = cv2.imread(str(TEMPLATES / f"gems_{d}.png"), cv2.IMREAD_GRAYSCALE)
        if img is not None:
            out[d] = img.astype(np.float32)
    return out


def _band(gray: np.ndarray, tab: str, r: int, c: int) -> np.ndarray:
    x, y = cell_origin(tab, r, c)
    return gray[y + BAND["y0"]:y + BAND["y1"], x + BAND["x0"]:x + BAND["x1"]].astype(np.float32)


def read_band(band: np.ndarray, rune: bool = False) -> int | None:
    """The count in one slot's band crop, or None if no digits (an empty slot, or a rune's lone dim 1)."""
    hits = []  # (score, x, w, digit, y)
    for d, t in _templates().items():
        if t.shape[0] > band.shape[0] or t.shape[1] > band.shape[1]:
            continue
        res = cv2.matchTemplate(band, t, cv2.TM_CCOEFF_NORMED)
        need = DIM_ONE_SCORE if (rune and d == "1") else MIN_SCORE
        for y, x in zip(*np.where(res >= min(need, FAINT_TENS))):
            hits.append((float(res[y, x]), int(x), t.shape[1], d, int(y)))
    strong = [h for h in hits if h[0] >= (DIM_ONE_SCORE if (rune and h[3] == "1") else MIN_SCORE)]
    # greedy, best first, no two digits overlapping (templates carry a 1 px margin: margins may touch). The "1" is
    # a bare bar that also fits the upright strokes of other digits: it ranks lower than its score
    strong.sort(key=lambda h: h[0] - (ONE_PENALTY if h[3] == "1" else 0), reverse=True)
    kept: list[tuple] = []
    for h in strong:
        if all(not _overlap(h, k) for k in kept):
            kept.append(h)
    if not kept:
        return None
    kept.sort(key=lambda k: k[1])
    # the count is the run of digits ending at the rightmost one, at most 2 (stacks stop at 99), each next to the
    # one after it; anything further left is the item's picture
    run = [kept[-1]]
    for k in reversed(kept[:-1]):
        if len(run) == 2 or not _adjacent(k, run[0]):
            break
        run.insert(0, k)
    if len(run) == 1 and run[0][3] != "1":  # a faint tens 1 right before the units digit
        tens = [h for h in hits if h[3] == "1" and _adjacent(h, run[0]) and not _overlap(h, run[0])
                and abs(h[4] - run[0][4]) <= 1 and (not rune or _bar_contrast(band, h) >= RUNE_TENS_CONTRAST)]
        if tens:
            run.insert(0, max(tens))
    return int("".join(k[3] for k in run))


def _overlap(a, b) -> bool:
    return not (a[1] + a[2] - 1 <= b[1] + 1 or b[1] + b[2] - 1 <= a[1] + 1)


def _adjacent(left, right) -> bool:
    return 0 <= right[1] - (left[1] + left[2]) + 1 <= 3


def _bar_contrast(band: np.ndarray, hit) -> float:
    """How much brighter a "1" match's bar is than the stone just left and right of it."""
    x, y = hit[1], hit[4]
    rows = band[y + 1:y + 9]
    bar = rows[:, x + 1:x + 3].mean()
    left, right = rows[:, max(0, x - 1):x + 1], rows[:, x + 3:x + 5]
    return float(bar - max(left.mean() if left.size else 0, right.mean() if right.size else 0))


def read_tab(frame: np.ndarray, tab: str) -> dict[tuple[int, int], int]:
    """{(row, col): count} for every slot on the tab; 0 where no count shows."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    t = TABS[tab]
    slots = RUNE_SLOTS if tab == "runes" else [(r, c) for r in range(t["rows"]) for c in range(t["cols"])]
    return {rc: read_band(_band(gray, tab, *rc), rune=tab == "runes") or 0 for rc in slots}


def rune_counts(frame: np.ndarray) -> dict[str, int]:
    from ..cube import RUNES
    counts = read_tab(frame, "runes")
    return {name: counts[rc] for name, rc in zip(RUNES, RUNE_SLOTS)}


def gem_name(r: int, c: int) -> str:
    return f"{GEM_GRADES[r]} {GEM_COLORS[c]}".strip()


def gem_counts(frame: np.ndarray) -> dict[str, int]:
    return {gem_name(r, c): n for (r, c), n in read_tab(frame, "gems").items()}
