"""Detect the name tooltip D2R draws above a hovered object/NPC: a near-black box with bright text.

Shape-based (not frame differencing), so moving NPCs or the camera don't cause false hits.
"""
from __future__ import annotations

import cv2
import numpy as np


def find_tooltip(frame: np.ndarray, x: int, y: int, above: int = 140, half_w: int = 140,
                 max_w: int = 260, min_w: int = 36) -> tuple[int, int, int, int] | None:
    """Look for a tooltip box in the area above (x, y). Returns its (x, y, w, h) or None."""
    x0, y0 = max(0, x - half_w), max(0, y - above)
    crop = frame[y0:y, x0 : x + half_w]
    if crop.size == 0:  # cursor at/over the top or left edge
        return None
    roi = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Tooltip boxes are pure black (~0-3); scenery shadows rarely are, so a low threshold keeps
    # the box from merging with dark surroundings.
    dark = (roi < 8).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 5), np.uint8))  # bridge the letters
    n, _, st, _ = cv2.connectedComponentsWithStats(dark)
    for i in range(1, n):
        bx, by, bw, bh, area = st[i]
        if not (min_w <= bw <= max_w and 14 <= bh <= 60):
            continue
        box = roi[by : by + bh, bx : bx + bw]
        fill = area / (bw * bh)
        bright = (box > 130).mean()
        if fill > 0.6 and 0.03 < bright < 0.5:
            return int(x0 + bx), int(y0 + by), int(bw), int(bh)
    return None


CHAT = (0, 440, 520, 150)  # chat lines (bottom left) come and go too
INFO = (1000, 0, 280, 140)  # area name, difficulty, terror zones (top right)


def find_label(before: np.ndarray, after: np.ndarray, min_w: int = 150,
               region: tuple[int, int, int, int] = (0, 30, 1280, 560),
               ignore: tuple[tuple[int, int, int, int], ...] = (CHAT, INFO)) -> tuple[int, int, int, int] | None:
    """A long name label that appeared between two frames (cursor parked, then hovering). Level exits
    draw "To The Durance of Hate Level 3" on a dark box that touches dark scenery, so the box can't
    be told apart by its shape alone (find_tooltip); what changed between the frames can."""
    rx, ry, rw, rh = region
    a = cv2.cvtColor(before[ry : ry + rh, rx : rx + rw], cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(after[ry : ry + rh, rx : rx + rw], cv2.COLOR_BGR2GRAY)
    diff = (cv2.absdiff(a, b) > 30).astype(np.uint8)
    for x, y, w, h in ignore:
        diff[max(0, y - ry) : max(0, y - ry + h), max(0, x - rx) : max(0, x - rx + w)] = 0
    diff = cv2.morphologyEx(diff, cv2.MORPH_CLOSE, np.ones((5, 15), np.uint8))  # letters -> a bar
    # keep long horizontal runs only: cuts the bar loose from her (idle animation, Energy Shield)
    diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, np.ones((1, min_w - 30), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(diff)
    best = None
    for i in range(1, n):
        bx, by, bw, bh, _ = st[i]
        if not (min_w <= bw <= 500 and 8 <= bh <= 45):
            continue
        box = b[by : by + bh, bx : bx + bw]
        dark, bright = (box < 16).mean(), (box > 130).mean()
        if dark > 0.3 and 0.03 < bright < 0.5 and (best is None or bw > best[2]):
            best = (int(rx + bx), int(ry + by), int(bw), int(bh))
    return best
