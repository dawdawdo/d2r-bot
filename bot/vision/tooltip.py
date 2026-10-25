"""Detect the name tooltip D2R draws above a hovered object/NPC: a near-black box with bright text.

Shape-based (not frame differencing), so moving NPCs or the camera don't cause false hits.
"""
from __future__ import annotations

import cv2
import numpy as np


def find_tooltip(frame: np.ndarray, x: int, y: int, above: int = 140, half_w: int = 140) -> tuple[int, int, int, int] | None:
    """Look for a tooltip box in the area above (x, y). Returns its (x, y, w, h) or None."""
    x0, y0 = max(0, x - half_w), max(0, y - above)
    roi = cv2.cvtColor(frame[y0:y, x0 : x + half_w], cv2.COLOR_BGR2GRAY)
    if roi.size == 0:
        return None
    dark = (roi < 22).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((3, 7), np.uint8))  # bridge the letters
    n, _, st, _ = cv2.connectedComponentsWithStats(dark)
    for i in range(1, n):
        bx, by, bw, bh, area = st[i]
        if not (40 <= bw <= 260 and 14 <= bh <= 60):
            continue
        box = roi[by : by + bh, bx : bx + bw]
        fill = area / (bw * bh)
        bright = (box > 130).mean()
        if fill > 0.6 and 0.03 < bright < 0.5:
            return int(x0 + bx), int(y0 + by), int(bw), int(bh)
    return None
