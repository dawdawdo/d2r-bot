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


def poisoned(frame: np.ndarray, hp_cfg: dict) -> bool:
    """The life orb is green: poisoned (every Andariel chicken frame on 2026-11-23). Green = the second colour range
    of vision.orbs.hp; true when it's most of the liquid."""
    ranges = hp_cfg["color"] if isinstance(hp_cfg["color"], list) else [hp_cfg["color"]]
    if len(ranges) < 2:
        return False
    sub = crop(frame, hp_cfg["region"])
    green = (hsv_mask(sub, ranges[1]) > 0).sum()
    red = (hsv_mask(sub, ranges[0]) > 0).sum()
    return bool(green > 40 and green > 2 * red)


def belt_slots(frame: np.ndarray, belt_cfg: dict) -> list[bool]:
    """Which visible belt slots (keys 1-4) hold a potion: potions are saturated, empty slots gray."""
    import cv2

    y0, y1 = belt_cfg["y"]
    hsv = cv2.cvtColor(frame[y0:y1], cv2.COLOR_BGR2HSV)
    return [bool((hsv[:, x - 10 : x + 10, 1] > 120).mean() > 0.15) for x in belt_cfg["x"]]


ANTIDOTE_MIN = 0.75  # belt_antidote.png: 1.00 on an antidote, <= 0.40 on potions and empty slots (2026-11-23)
_antidote_tpl = None


def _is_antidote(frame: np.ndarray, x: int, y0: int, y1: int) -> bool:
    """The pale antidote jar: hardly any saturated pixels, so the hue test below calls it empty."""
    import cv2

    global _antidote_tpl
    if _antidote_tpl is None:
        from .screen import ASSETS

        _antidote_tpl = cv2.imread(str(ASSETS / "belt_antidote.png"))
    reg = frame[max(0, y0 - 23):y1 - 6, max(0, x - 14):x + 14]
    if _antidote_tpl is None or reg.shape[0] < _antidote_tpl.shape[0] or reg.shape[1] < _antidote_tpl.shape[1]:
        return False
    return cv2.minMaxLoc(cv2.matchTemplate(reg, _antidote_tpl, cv2.TM_CCOEFF_NORMED))[1] >= ANTIDOTE_MIN


def belt_kinds(frame: np.ndarray, belt_cfg: dict) -> list[str | None]:
    """Per visible belt slot: 'hp' (red healing), 'mp' (blue mana), 'rejuv' (purple), 'antidote' or None (empty)."""
    import cv2

    y0, y1 = belt_cfg["y"]
    hsv = cv2.cvtColor(frame[y0:y1], cv2.COLOR_BGR2HSV)
    out: list[str | None] = []
    for x in belt_cfg["x"]:
        if _is_antidote(frame, x, y0, y1):
            out.append("antidote")
            continue
        px = hsv[:, x - 10 : x + 10].reshape(-1, 3)
        sat = px[px[:, 1] > 120]
        if len(sat) < 0.15 * len(px):
            out.append(None)
            continue
        h = np.median(sat[:, 0])  # OpenCV hue 0-180: red ~0/175, blue ~105-125, purple ~130-160
        out.append("mp" if 95 <= h < 128 else "rejuv" if 128 <= h < 165 else "hp")
    return out


def orb_pcts(frame: np.ndarray, orb_cfg: dict) -> dict[str, float]:
    """{'hp': 0-100, 'mp': 0-100} from config `vision.orbs`."""
    return {
        name: round(100 * orb_fill(frame, c["region"], c["color"]), 1)
        for name, c in orb_cfg.items()
    }
