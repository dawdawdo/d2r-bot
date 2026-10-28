"""Detect the name tooltip D2R draws above a hovered object/NPC: a near-black box with bright text.

Shape-based (not frame differencing), so moving NPCs or the camera don't cause false hits.
"""
from __future__ import annotations

import cv2
import numpy as np


def find_tooltip(frame: np.ndarray, x: int, y: int, above: int = 140, half_w: int = 140,
                 max_w: int = 260) -> tuple[int, int, int, int] | None:
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
        if not (36 <= bw <= max_w and 14 <= bh <= 60):
            continue
        box = roi[by : by + bh, bx : bx + bw]
        fill = area / (bw * bh)
        bright = (box > 130).mean()
        if fill > 0.6 and 0.03 < bright < 0.5:
            return int(x0 + bx), int(y0 + by), int(bw), int(bh)
    return None
