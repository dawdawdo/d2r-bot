"""A town as a set of views with known world positions (keyframes), for finding where we are from one frame.

World coordinates are screen pixels at 1280x720: a keyframe at (x, y) is a view whose centre is (x, y) px from
the map's origin. Two views of the same ground differ by a pure translation (fixed isometric camera), so the
offset is the mode of ORB match translations (moving NPCs and the player/merc at the centre vote elsewhere).

Built by tools/town_map.py (explore + record); used by bot.town to walk to a waypoint from any spawn.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

SCALE = 0.5          # features on half-size frames (speed); offsets are reported at full size
MIN_VOTES = 10       # grid cells (CELL px, half size) covered by matches agreeing on one translation
TOL = 3.0            # px (half size) for a match to agree with a translation
CELL = 40            # half-size px: a 640x360 view has 16x9 cells; one palm tree covers 2-4


def _mask(h: int, w: int) -> np.ndarray:
    """Ground only: no HUD, merc portrait, clock, or the player + merc at the centre (they move with the view)."""
    m = np.zeros((h, w), np.uint8)
    s = SCALE
    m[int(40 * s):int(575 * s), int(20 * s):int(1260 * s)] = 255
    m[: int(95 * s), : int(130 * s)] = 0          # merc portrait
    m[: int(60 * s), int(1080 * s):] = 0          # clock / area name
    m[int(250 * s):int(420 * s), int(560 * s):int(720 * s)] = 0  # player (and usually the merc)
    return m


_orb = cv2.ORB_create(2500)
_bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def features(frame: np.ndarray):
    g = cv2.cvtColor(cv2.resize(frame, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    return _orb.detectAndCompute(g, _mask(*g.shape))


def offset(fa, fb) -> tuple[tuple[float, float], int]:
    """Camera displacement from view a to view b (full-size px) and how many matches agree on it."""
    ka, da = fa
    kb, db = fb
    if da is None or db is None or len(ka) < 10 or len(kb) < 10:
        return (0.0, 0.0), 0
    ms = _bf.match(da, db)
    if len(ms) < MIN_VOTES:
        return (0.0, 0.0), 0
    v = np.array([np.subtract(ka[m.queryIdx].pt, kb[m.trainIdx].pt) for m in ms], np.float32)
    # mode by voting on a coarse grid, then refine on the agreeing matches
    # Score = how many grid cells of the view the agreeing matches cover, not how many there are: Lut Gholein
    # repeats sprites (palm trees, torches, wall segments), and one tree's 100+ features agree on a false
    # offset (2026-11-02: a tree matched a view 1000 px away). Real overlap agrees all over the ground.
    pb = np.array([kb[m.trainIdx].pt for m in ms], np.float32)
    q = np.round(v / TOL).astype(np.int32)
    keys, inv, counts = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    best, best_cells = None, 0
    for k in np.argsort(-counts)[:8]:
        if counts[k] < 6:
            break
        cand = v[inv.ravel() == k].mean(0)
        agree = np.linalg.norm(v - cand, axis=1) < TOL
        cells = len({(int(x // CELL), int(y // CELL)) for x, y in pb[agree]})
        if cells > best_cells:
            best, best_cells = agree, cells
    if best is None:
        return (0.0, 0.0), 0
    t = v[best].mean(0) / SCALE
    return (float(t[0]), float(t[1])), best_cells


@dataclass
class ViewMap:
    root: Path
    frames: list[dict] = field(default_factory=list)   # {"file", "x", "y"}
    targets: dict = field(default_factory=dict)          # name -> [x, y] world (e.g. "wp": the waypoint's centre)
    _feats: list = field(default_factory=list, repr=False)

    @classmethod
    def load(cls, root: str | Path) -> "ViewMap":
        root = Path(root)
        m = cls(root)
        idx = root / "index.json"
        if idx.exists():
            d = json.loads(idx.read_text())
            m.frames, m.targets = d["frames"], d.get("targets", {})
            m._feats = [features(cv2.imread(str(root / f["file"]))) for f in m.frames]
        return m

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "index.json").write_text(json.dumps({"frames": self.frames, "targets": self.targets}, indent=1))

    def add(self, frame: np.ndarray, pos: tuple[float, float]) -> None:
        name = f"{len(self.frames):03d}.jpg"
        self.root.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(self.root / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        self.frames.append({"file": name, "x": round(pos[0], 1), "y": round(pos[1], 1)})
        self._feats.append(features(frame))

    def nearest(self, pos: tuple[float, float]) -> float:
        if not self.frames:
            return float("inf")
        return min(np.hypot(f["x"] - pos[0], f["y"] - pos[1]) for f in self.frames)

    def locate(self, frame: np.ndarray, feats=None, near: tuple[float, float] | None = None,
               radius: float = 900) -> tuple[tuple[float, float], int] | None:
        """World position of this view: (pos, votes) from the best-agreeing keyframe, or None.
        `near`: only try keyframes within `radius` of a position guess (faster, fewer false matches)."""
        f = feats if feats is not None else features(frame)
        best = None
        for kf, kfeat in zip(self.frames, self._feats):
            if near is not None and np.hypot(kf["x"] - near[0], kf["y"] - near[1]) > radius:
                continue
            (dx, dy), n = offset(kfeat, f)
            if n >= MIN_VOTES and (best is None or n > best[1]):
                best = ((kf["x"] + dx, kf["y"] + dy), n)
        return best
