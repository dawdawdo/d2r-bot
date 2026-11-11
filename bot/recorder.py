"""Training-data recorders for the learned-perception plan (docs: "D2R Bot: Learned Perception Plan").

Both only watch; neither changes how she plays. Writes go to fixtures/raw/ (gitignored) on a background thread
so a JPEG encode never stalls a guard tick.

- FrameSampler: one 640x360 frame every `frame_every_s` while out of town, capped per day -> object detector data.
- DangerRecorder: the last `window_s` seconds out of town (vitals every tick, a 320x180 frame every `frame_dt_s`),
  dumped on a chicken, a death, a sharp life drop, or now and then at random (calm examples) -> danger predictor.
"""
from __future__ import annotations

import csv
import logging
import queue
import random
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


class _Writer:
    """One background thread that writes JPEGs and small text files."""

    def __init__(self) -> None:
        self.q: queue.Queue = queue.Queue(maxsize=200)
        threading.Thread(target=self._run, name="recorder-writer", daemon=True).start()

    def put(self, job) -> None:
        try:
            self.q.put_nowait(job)
        except queue.Full:  # never block the bot for training data
            pass

    def _run(self) -> None:
        while True:
            job = self.q.get()
            try:
                job()
            except Exception as ex:  # noqa: BLE001
                log.debug("recorder write failed: %s", ex)


def _jpg(path: Path, img: np.ndarray, quality: int = 85) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, quality])


class FrameSampler:
    def __init__(self, root: Path, every_s: float = 10.0, daily_cap: int = 3000, writer: _Writer | None = None,
                 clock=time.time) -> None:
        self.root, self.every, self.cap = Path(root), every_s, daily_cap
        self.writer = writer or _Writer()
        self.clock = clock
        self._next = 0.0
        self._day, self._count = "", 0

    def tick(self, frame: np.ndarray, tag: str = "") -> None:
        now = self.clock()
        if now < self._next:
            return
        self._next = now + self.every
        day = time.strftime("%Y%m%d", time.localtime(now))
        if day != self._day:
            self._day = day
            d = self.root / day
            self._count = len(list(d.glob("*.jpg"))) if d.exists() else 0
        if self._count >= self.cap:
            return
        self._count += 1
        small = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
        stamp = time.strftime("%H%M%S", time.localtime(now)) + f"{now % 1:.2f}"[1:]
        path = self.root / day / f"{day}-{stamp}_{tag or 'play'}.jpg"
        self.writer.put(lambda: _jpg(path, small))


class DangerRecorder:
    def __init__(self, root: Path, window_s: float = 5.0, frame_dt_s: float = 0.5, drop_pts: float = 30.0,
                 drop_within_s: float = 2.0, calm_p: float = 0.002, writer: _Writer | None = None,
                 clock=time.time, rng: random.Random | None = None) -> None:
        self.root = Path(root)
        self.window, self.frame_dt = window_s, frame_dt_s
        self.drop_pts, self.drop_within = drop_pts, drop_within_s
        self.calm_p = calm_p
        self.writer = writer or _Writer()
        self.clock = clock
        self.rng = rng or random.Random()
        self.vitals: deque = deque()   # (t, hp, mp)
        self.frames: deque = deque()   # (t, small frame)
        self._last_frame_t = -99.0
        self._quiet_until = 0.0        # one dump per incident
        self.dumps = 0

    def reset(self) -> None:
        """Back in town / new game: an old buffer must not leak into the next incident."""
        self.vitals.clear()
        self.frames.clear()

    def tick(self, frame: np.ndarray, hp: float | None, mp: float | None, tag: str = "") -> None:
        if hp is None:
            return
        now = self.clock()
        self.vitals.append((now, float(hp), float(mp if mp is not None else -1)))
        if now - self._last_frame_t >= self.frame_dt:
            self._last_frame_t = now
            self.frames.append((now, cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)))
        while self.vitals and now - self.vitals[0][0] > self.window:
            self.vitals.popleft()
        while self.frames and now - self.frames[0][0] > self.window:
            self.frames.popleft()
        recent = [v[1] for v in self.vitals if now - v[0] <= self.drop_within]
        if recent and max(recent) - hp >= self.drop_pts:
            self.event("drop", tag)
        elif self.rng.random() < self.calm_p and len(self.frames) >= int(self.window / self.frame_dt) - 1:
            self.event("calm", tag)

    def event(self, reason: str, tag: str = "") -> None:
        now = self.clock()
        if now < self._quiet_until and reason in ("drop", "calm"):
            return
        self._quiet_until = now + self.window
        if not self.vitals:
            return
        vit, frames = list(self.vitals), list(self.frames)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
        d = self.root / f"{stamp}_{reason}{'_' + tag if tag else ''}"
        self.dumps += 1

        def write() -> None:
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "vitals.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t_rel", "hp", "mp"])
                for t, h, m in vit:
                    w.writerow([round(t - now, 3), h, m])
            for t, img in frames:
                _jpg(d / f"{t - now:+.2f}.jpg", img, 80)

        self.writer.put(write)


class Recorders:
    """What the Controller holds: both recorders, sharing one writer thread."""

    def __init__(self, root: Path, cfg: dict | None = None) -> None:
        cfg = cfg or {}
        w = _Writer()
        self.frames = FrameSampler(Path(root) / "sampled", cfg.get("frame_every_s", 10.0),
                                   cfg.get("frame_daily_cap", 3000), writer=w)
        self.danger = DangerRecorder(Path(root) / "danger", writer=w, calm_p=cfg.get("calm_p", 0.002))

    def tick(self, frame: np.ndarray, hp, mp, tag: str = "") -> None:
        self.frames.tick(frame, tag)
        self.danger.tick(frame, hp, mp, tag)

    def event(self, reason: str, tag: str = "") -> None:
        self.danger.event(reason, tag)

    def reset(self) -> None:
        self.danger.reset()
