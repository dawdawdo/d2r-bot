"""HP/MP orb fill percentage.

The orb's liquid fills from the bottom. Within the orb region we mark each row as
"filled" if enough of its pixels match the liquid color, then report the fraction of
rows from the top-most filled row down to the bottom of the region.
"""
from __future__ import annotations

import numpy as np

from .color import crop, hsv_mask


def orb_fill(frame: np.ndarray, region, color_range: dict, row_frac: float = 0.25) -> float:
    """Return fill in [0, 1]. `region` = (x, y, w, h) tightly around the liquid area.
    `color_range` may be a list of ranges (e.g. red, plus green when poisoned)."""
    sub = crop(frame, region)
    ranges = color_range if isinstance(color_range, list) else [color_range]
    mask = np.zeros(sub.shape[:2], bool)
    for r in ranges:
        mask |= hsv_mask(sub, r) > 0
    rows = mask.mean(axis=1) >= row_frac
    if not rows.any():
        return 0.0
    top = int(np.argmax(rows))
    return (len(rows) - top) / len(rows)


def belt_slots(frame: np.ndarray, belt_cfg: dict) -> list[bool]:
    """Which visible belt slots (keys 1-4) hold a potion: potions are saturated, empty slots gray."""
    import cv2

    y0, y1 = belt_cfg["y"]
    hsv = cv2.cvtColor(frame[y0:y1], cv2.COLOR_BGR2HSV)
    return [bool((hsv[:, x - 10 : x + 10, 1] > 120).mean() > 0.15) for x in belt_cfg["x"]]


def orb_pcts(frame: np.ndarray, orb_cfg: dict) -> dict[str, float]:
    """{'hp': 0-100, 'mp': 0-100} from config `vision.orbs`."""
    return {
        name: round(100 * orb_fill(frame, c["region"], c["color"]), 1)
        for name, c in orb_cfg.items()
    }
