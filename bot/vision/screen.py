"""Screen-state classification by template matching.

Each state lists one or more cues: a template image (in bot/assets/templates/) searched
for inside a region. A state matches when all its cues match. States are checked in
config order, so put specific states (dead, waypoint menu) before general ones (in_game).
A frame that is almost entirely black is "loading".

A template may have a mask next to it (`<name>_mask.png`, white = compare, black = ignore):
use it when the template has scenery showing through (e.g. text over the character-select
scene, which differs between machines/acts).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .color import crop

log = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "templates"
UNKNOWN = "unknown"
LOADING = "loading"


@dataclass
class Cue:
    template: np.ndarray
    region: tuple[int, int, int, int]
    threshold: float
    mask: np.ndarray | None = None


def match_score(frame: np.ndarray, template: np.ndarray, region=None,
                mask: np.ndarray | None = None) -> tuple[float, tuple[int, int]]:
    """Best normalized correlation of `template` in `region`; returns (score, (x, y) in frame).
    With `mask` (same shape as the template), only the mask's nonzero pixels are compared."""
    hay = crop(frame, region) if region else frame
    if hay.shape[0] < template.shape[0] or hay.shape[1] < template.shape[1]:
        return 0.0, (0, 0)
    res = cv2.matchTemplate(hay, template, cv2.TM_CCOEFF_NORMED, mask=mask)
    if mask is not None:
        res[~np.isfinite(res)] = 0  # flat patches under the mask give NaN/inf
    _, score, _, loc = cv2.minMaxLoc(res)
    ox, oy = (region[0], region[1]) if region else (0, 0)
    return float(score), (loc[0] + ox, loc[1] + oy)


def is_loading(frame: np.ndarray, max_mean: float = 12.0, max_bright_frac: float = 0.01) -> bool:
    """Black frame, or D2R's loading card: a framed picture centered on black margins.
    Only used as a fallback after template states (so in-game darkness with a HUD is excluded)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if gray.mean() < max_mean and (gray > 60).mean() < max_bright_frac:
        return True
    w = gray.shape[1]
    sides = np.hstack([gray[:, : w // 4], gray[:, -w // 4 :]])
    return sides.mean() < 4 and (sides > 40).mean() < 0.002


class ScreenClassifier:
    def __init__(self, states: dict[str, list[Cue]]) -> None:
        self.states = states

    @classmethod
    def from_config(cls, states_cfg: dict, assets: Path = ASSETS) -> "ScreenClassifier":
        states: dict[str, list[Cue]] = {}
        for name, cues in (states_cfg or {}).items():
            loaded = []
            for c in cues:
                path = assets / c["template"]
                img = cv2.imread(str(path))
                if img is None:
                    log.warning("state %s: missing template %s (state disabled)", name, path.name)
                    loaded = []
                    break
                mask_path = path.with_name(path.stem + "_mask" + path.suffix)
                mask = cv2.imread(str(mask_path)) if mask_path.exists() else None
                if mask is not None:
                    mask = (mask > 127).astype(np.uint8)
                loaded.append(Cue(img, tuple(c["region"]), float(c.get("threshold", 0.85)), mask))
            if loaded:
                states[name] = loaded
        return cls(states)

    def classify(self, frame: np.ndarray) -> str:
        for name, cues in self.states.items():
            if all(match_score(frame, c.template, c.region, c.mask)[0] >= c.threshold for c in cues):
                return name
        if is_loading(frame):
            return LOADING
        return UNKNOWN
