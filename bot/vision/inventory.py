"""Inventory grid (10 x 4 cells, right panel; open with the inventory key or the stash).

Measured 2026-10-26 at 1280x720: cell (0, 0) interior starts at (867, 350), 35 px wide, pitch 37.8 px.
Cells are addressed (col, row).
"""
from __future__ import annotations

import cv2
import numpy as np

X0, Y0, PITCH, SIZE = 867, 350, 37.8, 35
COLS, ROWS = 10, 4
KEY_SCORE = 0.9  # inv_key.png scores 1.00 on keys, < 0.3 on everything else in the fixtures


def cell_xy(c: int, r: int) -> tuple[int, int]:
    """Top-left of the cell's interior."""
    return int(round(X0 + c * PITCH)), int(round(Y0 + r * PITCH))


def cell_center(c: int, r: int) -> tuple[int, int]:
    x, y = cell_xy(c, r)
    return x + SIZE // 2, y + SIZE // 2


def _cell(frame: np.ndarray, c: int, r: int) -> np.ndarray:
    x, y = cell_xy(c, r)
    return frame[y : y + SIZE, x : x + SIZE]


def is_empty(frame: np.ndarray, c: int, r: int) -> bool:
    """Empty cells are flat dark gray (mean ~10, 98th percentile <= 44); items are much brighter."""
    g = cv2.cvtColor(_cell(frame, c, r), cv2.COLOR_BGR2GRAY)
    return float(g.mean()) < 20 and float(np.percentile(g, 98)) < 60


def is_key(frame: np.ndarray, c: int, r: int, template: np.ndarray) -> bool:
    return float(cv2.matchTemplate(_cell(frame, c, r), template, cv2.TM_CCOEFF_NORMED).max()) >= KEY_SCORE


def protected_cells(rects) -> set[tuple[int, int]]:
    """Config `inventory.protected`: [c, r, w, h] rectangles of Stephen's own items (charms, tomes, cube)."""
    return {(c + i, r + j) for c, r, w, h in rects for i in range(w) for j in range(h)}


def scan(frame: np.ndarray, key_template: np.ndarray, protected=()) -> dict[str, list[tuple[int, int]]]:
    """Classify unprotected cells, column by column: empty, key, or other (loot to stash)."""
    prot = set(protected)
    out: dict[str, list[tuple[int, int]]] = {"empty": [], "key": [], "other": []}
    for c in range(COLS):
        for r in range(ROWS):
            if (c, r) in prot:
                continue
            if is_empty(frame, c, r):
                out["empty"].append((c, r))
            elif is_key(frame, c, r, key_template):
                out["key"].append((c, r))
            else:
                out["other"].append((c, r))
    return out
