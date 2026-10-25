"""HSV color-range masks. Ranges use OpenCV HSV (H 0-179, S/V 0-255).

A range is {"lo": [h, s, v], "hi": [h, s, v]}; if lo.h > hi.h the hue wraps (e.g. red).
"""
from __future__ import annotations

import cv2
import numpy as np


def hsv_mask(bgr: np.ndarray, rng: dict) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lo, hi = np.array(rng["lo"]), np.array(rng["hi"])
    if lo[0] <= hi[0]:
        return cv2.inRange(hsv, lo, hi)
    a = cv2.inRange(hsv, lo, np.array([179, hi[1], hi[2]]))
    b = cv2.inRange(hsv, np.array([0, lo[1], lo[2]]), hi)
    return cv2.bitwise_or(a, b)


def crop(frame: np.ndarray, region) -> np.ndarray:
    x, y, w, h = region
    return frame[y : y + h, x : x + w]
