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


WHITE_TEXT = {"lo": [0, 0, 190], "hi": [179, 40, 255]}
MAX_COLOR_H = 16  # rune labels in 22 live picks: 13-14 px tall
COLOR_BG_DARK, COLOR_BG_MEAN = 0.78, 25
MAX_RUN = 14      # longest horizontal run of text pixels: runes <= 12 ("M"), coin piles 16-17
SPRITE_MAX_H = 60  # a label merged with its item sprite (rings, amulets, runes: small)
ON_BOX = 0.4      # share of near-black pixels in a 7x7 around label text; lit ground has none


def _max_run(m: np.ndarray) -> int:
    best = 0
    for row in m:
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        if starts.size:
            best = max(best, int((ends - starts).max()))
    return best


def _passes(frame: np.ndarray, gray: np.ndarray, mask: np.ndarray, kind: str, x: int, y: int, w: int, h: int,
            max_bg: float, min_pad_dark: float, min_bg_dark: float) -> bool:
    text = mask[y : y + h, x : x + w] > 0
    if not 0.08 <= text.mean() <= 0.22:  # label text fills 12-14% of its 13 px tall box (live);
        return False                     # coins between two labels: 27%, 8 px tall
    if kind != "white":  # white text in the box: the gap between two gold labels where the
        # coins underneath show through (2026-10-27 read as a unique next to "1818 Gold")
        white = hsv_mask(frame[y : y + h, x : x + w], WHITE_TEXT) > 0
        if white.sum() > 0.15 * text.sum():  # real rune labels: 0 white px
            return False
        # coin piles are solid blobs: real label text is 13-14 px tall with strokes of <= 12 px
        if h > MAX_COLOR_H or _max_run(text) > MAX_RUN:
            return False
        bgc = gray[y : y + h, x : x + w][~text]  # the backdrop box: 34 live rune picks >= 81% dark,
        if bgc.size and ((bgc < 25).mean() < COLOR_BG_DARK or bgc.mean() > COLOR_BG_MEAN):  # mean <= 20;
            return False  # coins/monsters between gold labels: <= 73% dark, mean >= 28
    bg = gray[y : y + h, x : x + w][~text]
    if bg.size and (bg.mean() > max_bg or (bg < 25).mean() < min_bg_dark):
        return False  # label text sits on a near-black box; gold piles sit on lit ground
    # The backdrop box extends a few px above and below the text. Gold piles and other
    # yellowish ground sprites pass the color test but have lit ground there.
    pad = np.concatenate([gray[max(0, y - 3) : max(0, y - 1), x : x + w].ravel(),
                          gray[y + h + 1 : y + h + 3, x : x + w].ravel()])
    return not (pad.size and (pad < 25).mean() < min_pad_dark)


def _labels_beside_sprite(gray: np.ndarray, mask: np.ndarray, x: int, y: int, w: int, h: int, min_w: int, min_h: int,
                          accept) -> list[tuple[int, int, int, int]]:
    """Labels whose item sprite is the same color and touches them (2026-11-03 21:24: a unique ring's cream sprite
    merged with its "Ring" label, so she left it on the ground). Keep only the color pixels on a mostly black
    surrounding: the text sits on its backdrop box, the sprite on lit ground. Then look for labels again."""
    near_black = cv2.boxFilter((gray[y : y + h, x : x + w] < 25).astype(np.float32), -1, (7, 7))
    clean = np.zeros_like(mask)
    clean[y : y + h, x : x + w] = np.where(near_black >= ON_BOX, mask[y : y + h, x : x + w], 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
    n, _, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(clean, kernel), connectivity=8)
    boxes = [tuple(int(v) for v in stats[i][:4]) for i in range(1, n)]
    return [b for b in boxes if b[2] >= min_w and min_h <= b[3] <= MAX_COLOR_H and accept(clean, *b)]


def find_labels(frame: np.ndarray, kinds: dict[str, dict], min_w: int = 20, min_h: int = 11,
                max_h: int = 30, ignore: list | None = None, max_bg: float = 45.0,
                min_pad_dark: float = 0.6, min_bg_dark: float = 0.6) -> list[Label]:
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

        def ok(m: np.ndarray, ax: int, ay: int, aw: int, ah: int) -> bool:
            return _passes(frame, gray, m, kind, ax, ay, aw, ah, max_bg, min_pad_dark, min_bg_dark)

        for i in range(1, n):
            x, y, w, h, area = (int(v) for v in stats[i])
            if w < min_w or h < min_h:
                continue
            if h <= max_h and ok(mask, x, y, w, h):
                out.append(Label(kind, x, y, w, h))
            elif kind != "white" and h <= SPRITE_MAX_H:
                out += [Label(kind, *b) for b in _labels_beside_sprite(gray, mask, x, y, w, h, min_w, min_h, ok)]
    return sorted(out, key=lambda l: (l.y, l.x))


WORD_TEMPLATES = {"key": "label_key.png", "rejuv": "label_rejuv.png", "gold": "label_gold.png"}  # "Rejuvenation" word: also Full Rejuvs
_words: dict[str, np.ndarray] = {}


def white_word(frame: np.ndarray, lab: Label, min_score: float = 0.75) -> str | None:
    """Which wanted white label this is ("key", "rejuv"), by matching the label's first word
    against a template; None for gold amounts and anything else."""
    from .screen import ASSETS

    gray = None
    for word, fname in WORD_TEMPLATES.items():
        t = _words.get(word)
        if t is None:
            t = _words[word] = cv2.imread(str(ASSETS / fname), cv2.IMREAD_GRAYSCALE)
        th, tw = t.shape
        if abs(lab.w - tw) > 4 or abs(lab.h - th) > 3:
            continue
        if gray is None:
            y0, x0 = max(0, lab.y - 3), max(0, lab.x - 3)
            gray = cv2.cvtColor(frame[y0 : lab.y + lab.h + 3, x0 : lab.x + lab.w + 3], cv2.COLOR_BGR2GRAY)
        if gray.shape[0] < th or gray.shape[1] < tw:
            continue
        if cv2.minMaxLoc(cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED))[1] >= min_score:
            return word
    return None


CHARM_SCORE = 0.8  # word_charm.png: 1.00 on "Small Charm"; <= 0.31 on an "Amulet" label, <= 0.65 on rune/rejuv tooltips


def has_word(gray: np.ndarray, fname: str, min_score: float = CHARM_SCORE) -> bool:
    """`fname` (a word cut from a tooltip; ground labels use the same font) appears in this grayscale crop."""
    from .screen import ASSETS

    t = _words.get(fname)
    if t is None:
        t = _words[fname] = cv2.imread(str(ASSETS / fname), cv2.IMREAD_GRAYSCALE)
    if gray.shape[0] < t.shape[0] or gray.shape[1] < t.shape[1]:
        return False
    return cv2.minMaxLoc(cv2.matchTemplate(gray, t, cv2.TM_CCOEFF_NORMED))[1] >= min_score


def is_charm(frame: np.ndarray, lab: Label) -> bool:
    """A blue label that says "... Charm". Other magic items show too ("Eligible for Chronicle" items get past
    the filter's hide rules: a magic Amulet 2026-10-31), so the color alone isn't enough."""
    y0, x0 = max(0, lab.y - 4), max(0, lab.x - 4)
    return has_word(cv2.cvtColor(frame[y0 : lab.y + lab.h + 4, x0 : lab.x + lab.w + 4], cv2.COLOR_BGR2GRAY),
                    "word_charm.png")
