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
    """Empty cells are flat dark gray (mean ~10, 98th percentile <= 44); items are much brighter. The 2 px rim is left
    out: a lit grid line next to Stephen's items filled cell (3, 0)'s left column, an "item" no stash page took, and
    the stash counted as full (2026-11-07 08:14)."""
    g = cv2.cvtColor(_cell(frame, c, r), cv2.COLOR_BGR2GRAY)[2:-2, 2:-2]
    return float(g.mean()) < 20 and float(np.percentile(g, 98)) < 60


def is_key(frame: np.ndarray, c: int, r: int, template: np.ndarray) -> bool:
    return float(cv2.matchTemplate(_cell(frame, c, r), template, cv2.TM_CCOEFF_NORMED).max()) >= KEY_SCORE


# The "I" / "II" weapon tabs above the left hand (inventory open): the active one is bright (~93 vs ~46, 2026-11-03).
WEAPON_TABS = {1: (872, 72, 36, 14), 2: (912, 72, 36, 14)}


_INV_OPEN: list = []


def inventory_open(frame: np.ndarray) -> bool:
    """The inventory panel's "Inventory" header shows (1.00 GLaDOS, 0.98 Windows fixtures; closed <= 0.14)."""
    if not _INV_OPEN:
        from .screen import ASSETS

        _INV_OPEN.append(cv2.imread(str(ASSETS / "inventory_open.png")))
    return float(cv2.matchTemplate(frame[10:70, 940:1160], _INV_OPEN[0], cv2.TM_CCOEFF_NORMED).max()) >= 0.7


def weapon_set(frame: np.ndarray) -> int | None:
    """Active weapon set (1 or 2) with the inventory open; None if the tabs don't read clearly."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    m = {n: float(g[y : y + h, x : x + w].mean()) for n, (x, y, w, h) in WEAPON_TABS.items()}
    if abs(m[1] - m[2]) < 20:
        return None
    return 1 if m[1] > m[2] else 2


def protected_cells(rects) -> set[tuple[int, int]]:
    """Config `inventory.protected`: [c, r, w, h] rectangles of Stephen's own items (charms, tomes, cube)."""
    return {(c + i, r + j) for c, r, w, h in rects for i in range(w) for j in range(h)}


POTION_PX = 0.08  # share of strongly red or blue pixels: healing potions read 0.12-0.13, mana 0.10 (missed at 0.10 on 11-13), other unprotected items <= 0.07


def potion_kind(frame: np.ndarray, c: int, r: int) -> str | None:
    """'hp' / 'mp' for a healing / mana potion in this cell, else None (rejuvs, purple, are left alone)."""
    import cv2

    x, y = cell_xy(c, r)
    p = cv2.cvtColor(frame[y + 3 : y + SIZE - 3, x + 3 : x + SIZE - 3], cv2.COLOR_BGR2HSV)
    h, s, v = p[..., 0], p[..., 1], p[..., 2]
    if (((h <= 6) | (h >= 172)) & (s >= 150) & (v >= 110)).mean() >= POTION_PX:
        return "hp"
    if ((h >= 100) & (h <= 125) & (s >= 150) & (v >= 120)).mean() >= POTION_PX:
        return "mp"
    return None


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


# Stash Runes tab: one slot per rune, El..Zod row by row, 9 per row (measured 2026-10-26).
RUNES = ("El Eld Tir Nef Eth Ith Tal Ral Ort Thul Amn Sol Shael Dol Hel Io Lum Ko Fal Lem Pul Um Mal Ist "
         "Gul Vex Ohm Lo Sur Ber Jah Cham Zod").split()
RUNE_X0, RUNE_Y0, RUNE_PITCH_X, RUNE_PITCH_Y = 63, 125, 40.3, 40


def rune_slot_center(i: int) -> tuple[int, int]:
    return int(round(RUNE_X0 + (i % 9) * RUNE_PITCH_X)), int(round(RUNE_Y0 + (i // 9) * RUNE_PITCH_Y))


def runes_added(before: np.ndarray, after: np.ndarray) -> list[str]:
    """Rune slots whose picture (icon brightness or count digit) changed between two Runes-tab frames."""
    out = []
    for i, name in enumerate(RUNES):
        x, y = rune_slot_center(i)
        a, b = before[y - 18 : y + 18, x - 18 : x + 18], after[y - 18 : y + 18, x - 18 : x + 18]
        if int((np.abs(a.astype(np.int16) - b).max(axis=2) > 40).sum()) > 8:
            out.append(name)
    return out
