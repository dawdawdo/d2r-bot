"""Item labels (shown with Alt) found by text color.

Each label kind (unique, set, rune, ...) has an HSV range. Matching text pixels are
dilated horizontally so the letters of one label merge into a single box.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .color import hsv_mask


@dataclass(frozen=True)
class Label:
    kind: str
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


def find_labels(frame: np.ndarray, kinds: dict[str, dict], min_w: int = 20, min_h: int = 6,
                max_h: int = 30, ignore: list | None = None, max_bg: float = 45.0) -> list[Label]:
    """`kinds` maps kind -> HSV range. `ignore` = list of (x, y, w, h) regions (HUD etc.).
    Labels sit on a dark backdrop box, so candidates whose non-text pixels are brighter
    than `max_bg` (gray mean) are rejected."""
    out: list[Label] = []
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for kind, rng in kinds.items():
        mask = hsv_mask(frame, rng)
        for (ix, iy, iw, ih) in ignore or []:
            mask[iy : iy + ih, ix : ix + iw] = 0
        merged = cv2.dilate(mask, kernel)
        n, _, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if w < min_w or h < min_h or h > max_h:
                continue
            text = mask[y : y + h, x : x + w] > 0
            if text.mean() < 0.08:  # too sparse to be text
                continue
            bg = gray[y : y + h, x : x + w][~text]
            if bg.size and bg.mean() > max_bg:
                continue
            out.append(Label(kind, int(x), int(y), int(w), int(h)))
    return sorted(out, key=lambda l: (l.y, l.x))
