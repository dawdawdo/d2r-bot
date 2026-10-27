"""Is an equipped item at full durability? From its tooltip line "Durability: X of Y", without OCR:
the item is full exactly when the pictures of X and Y are the same. Also "Quantity: X of 12" (keys).

Templates (bot/assets/templates): tt_durability.png ("Durability:"), tt_of.png ("of"), cut from
the Shako tooltip on 2026-10-27.
"""
from __future__ import annotations

import cv2
import numpy as np

from .screen import ASSETS

_T: dict[str, np.ndarray] = {}
LINE_W = 150  # px after "Durability:" that hold "X of Y"


def _tpl(name: str) -> np.ndarray:
    if name not in _T:
        _T[name] = cv2.cvtColor(cv2.imread(str(ASSETS / name)), cv2.COLOR_BGR2GRAY)
    return _T[name]


def _trim(b: np.ndarray) -> np.ndarray:
    cols = np.nonzero(b.any(axis=0))[0]
    return b[:, cols[0] : cols[-1] + 1] if cols.size else b[:, :0]


def durability_numbers(frame: np.ndarray, word_tpl: str = "tt_durability.png") -> tuple[np.ndarray, np.ndarray] | None:
    """Binary pictures of X and Y in "<word> X of Y", or None when there's no such line (item has none,
    no tooltip). `word_tpl`: tt_durability.png or tt_quantity.png (key stacks)."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    word = _tpl(word_tpl)
    r = cv2.matchTemplate(g, word, cv2.TM_CCOEFF_NORMED)
    _, score, _, (x, y) = cv2.minMaxLoc(r)
    if score < 0.8:
        return None
    h, w = word.shape
    line = g[y : y + h, x + w : min(g.shape[1], x + w + LINE_W)]
    of = _tpl("tt_of.png")
    if line.shape[1] < of.shape[1]:
        return None
    r = cv2.matchTemplate(line, of, cv2.TM_CCOEFF_NORMED)
    _, s2, _, (ox, _) = cv2.minMaxLoc(r)
    if s2 < 0.7:
        return None
    b = line > 120
    left, right = _trim(b[:, :ox]), _trim(b[:, ox + of.shape[1] + 3 :])  # +3: the "f" can stick out
    # the right number ends where the line's text does: cut at the first wide gap
    cols = right.any(axis=0)
    gap = 0
    for i, c in enumerate(cols):
        gap = 0 if c else gap + 1
        if gap > 14:  # digit spacing reaches ~9 px ("1" is narrow)
            right = _trim(right[:, :i])
            break
    return left, right


def durability_full(frame: np.ndarray, word_tpl: str = "tt_durability.png") -> bool | None:
    """True = X == Y (full), False = lower, None = no such line found."""
    nums = durability_numbers(frame, word_tpl)
    if nums is None:
        return None
    a, b = nums
    if a.shape != b.shape:
        return False
    return float((a != b).mean()) < 0.08


def _glyphs(b: np.ndarray) -> list[np.ndarray]:
    """Split a binary number picture into digit pictures at blank columns."""
    cols = b.any(axis=0)
    out, start = [], None
    for i, c in enumerate(list(cols) + [False]):
        if c and start is None:
            start = i
        elif not c and start is not None:
            out.append(b[:, start:i])
            start = None
    return out


def _same(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and float((a != b).mean()) < 0.08


def key_count(frame: np.ndarray) -> int | None:
    """Lower bound on the keys in a hovered stack, from "Quantity: N of 12" using the "1" and "2"
    of the "12" as the only known glyphs: 12, 11, 10, 3 (meaning 3-9), 2 or 1. None: no such line."""
    nums = durability_numbers(frame, "tt_quantity.png")
    if nums is None:
        return None
    left, right = (_glyphs(x) for x in nums)
    if len(right) != 2:
        return None
    one, two = right
    if len(left) == 2:
        return 12 if _same(left[1], two) else 11 if _same(left[1], one) else 10
    if len(left) == 1:
        return 1 if _same(left[0], one) else 2 if _same(left[0], two) else 3
    return None
