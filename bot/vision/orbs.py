"""HP/MP orb fill percentage.

The orb's liquid fills from the bottom. Within the orb region we mark each row as
"filled" if enough of its pixels match the liquid color, then report the fraction of
rows from the top-most filled row down to the bottom of the region.
"""
from __future__ import annotations

import numpy as np

from .color import crop, hsv_mask


def orb_fill(frame: np.ndarray, region, color_range: dict, row_frac: float = 0.25) -> float:
    """Return fill in [0, 1]. `region` = (x, y, w, h) tightly around the liquid area."""
    mask = hsv_mask(crop(frame, region), color_range) > 0
    rows = mask.mean(axis=1) >= row_frac
    if not rows.any():
        return 0.0
    top = int(np.argmax(rows))
    return (len(rows) - top) / len(rows)


def orb_pcts(frame: np.ndarray, orb_cfg: dict) -> dict[str, float]:
    """{'hp': 0-100, 'mp': 0-100} from config `vision.orbs`."""
    return {
        name: round(100 * orb_fill(frame, c["region"], c["color"]), 1)
        for name, c in orb_cfg.items()
    }
