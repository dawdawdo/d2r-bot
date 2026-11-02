"""The hovered monster's name bar (top centre): a box with the name, red as far as its life goes,
the monster type ("Demon") underneath. While casting, the cursor sits on the target, so the bar says
what's under the target and how much life it has left (Stephen's Meph kill, 2026-10-30 views 100-148).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
BAR = (520, 12, 240, 32)  # x, y, w, h full-res: the name box (Mephisto's: x 585-697, y ~18-38)
CENTER_X = 640  # the box is centred here
_T: dict = {}


def _red(strip: np.ndarray) -> np.ndarray:
    s = strip.astype(np.int16)
    b, g, r = s[..., 0], s[..., 1], s[..., 2]
    return (r > 60) & (r > 2 * g) & (r > 2 * b)


def _text(strip: np.ndarray) -> np.ndarray:
    """The name's letters: bright and unsaturated (cream on red or on the dark rest of the box)."""
    return (strip.min(axis=2) > 115).astype(np.float32)


def name_bar(frame: np.ndarray) -> dict | None:
    """{'life': 0..1, 'mephisto': bool} if a name bar shows, else None. Mephisto's name over an
    empty box = life 0: he's dying (the 2026-11-01 21:23 kill: name, no red, soul rising)."""
    x, y, w, h = BAR
    strip = frame[y : y + h, x : x + w]
    red = _red(strip)
    if red.mean() < 0.05:
        if is_mephisto(frame):
            return {"life": 0.0, "mephisto": True}
        return None  # no box (or another monster at 0 life)
    cols = np.nonzero(red.mean(axis=0) > 0.3)[0]
    if not len(cols):
        return None
    left, right = x + cols[0], x + cols[-1]
    width = max(2 * (CENTER_X - left), 1)
    life = float(np.clip((right - left + 1) / width, 0, 1))
    return {"life": life, "mephisto": is_mephisto(frame)}


def is_mephisto(frame: np.ndarray, thresh: float = 0.6) -> bool:
    if "meph" not in _T:
        t = cv2.imread(str(TEMPLATES / "name_mephisto.png"))
        _T["meph"] = _text(t)
    x, y, w, h = BAR
    txt = _text(frame[y : y + h, x : x + w])
    t = _T["meph"]
    if txt.sum() < 0.5 * t.sum():
        return False
    return float(cv2.matchTemplate(txt, t, cv2.TM_CCORR_NORMED).max()) >= thresh
