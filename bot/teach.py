"""Teach-and-repeat: record a route Stephen plays (tools/record_route.py), for the bot to replay.

Each of his clicks becomes a step: button, client position, the automap fix after it (world px from
the waypoint arrival, on the Durance 2 canvas), and the view (saved as a jpg for view matching on
replay). Right-clicks are teleports, the left click at the end is the stairs. Clicks run on the
listener thread; frames are grabbed on a worker thread SETTLE s later, when the teleport has landed.
"""
from __future__ import annotations

import json
import logging
import queue
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from .nav import CENTER

log = logging.getLogger(__name__)

SETTLE = 0.35  # s after a click: the teleport has landed (nav.TP_SETTLE 0.16 + the automap redraw)


class RouteRecorder:
    def __init__(self, capture, odo, client_origin: tuple[int, int], folder: Path,
                 clock=time.monotonic, sleep=time.sleep) -> None:
        self.capture, self.odo, self.folder = capture, odo, folder
        self.ox, self.oy = client_origin
        self.clock, self.sleep = clock, sleep
        self.steps: list[dict] = []
        self.q: queue.Queue = queue.Queue()
        self.t0 = clock()
        (folder / "views").mkdir(parents=True, exist_ok=True)
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    # --- listener thread --------------------------------------------------------------------------
    def on_click(self, x: int, y: int, button: str) -> None:
        cx, cy = x - self.ox, y - self.oy
        if 0 <= cx < 1280 and 0 <= cy < 720:
            self.q.put((self.clock(), cx, cy, button))

    # --- worker thread ----------------------------------------------------------------------------
    def _run(self) -> None:
        while True:
            item = self.q.get()
            if item is None:
                return
            try:
                self._step(*item)
            except Exception:
                log.exception("recording a step failed")

    def _step(self, t: float, cx: int, cy: int, button: str) -> None:
        wait = t + SETTLE - self.clock()
        if wait > 0:
            self.sleep(wait)
        frame = self.capture.grab()
        expect = (cx - CENTER[0], cy - CENTER[1]) if button == "right" else None
        before = self.odo.pos.copy()
        self.odo.update(frame, expect=expect)
        i = len(self.steps)
        name = f"views/{i:03d}.jpg"
        cv2.imwrite(str(self.folder / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        step = {"i": i, "t": round(t - self.t0, 2), "button": button, "click": [cx, cy],
                "from": [round(float(v), 1) for v in before], "pos": [round(float(v), 1) for v in self.odo.pos],
                "resp": round(float(self.odo.resp), 3), "lost": bool(self.odo.lost), "view": name}
        self.steps.append(step)
        log.info("step %d: %s click (%d, %d) -> pos %s (resp %.2f%s)", i, button, cx, cy, step["pos"],
                 step["resp"], ", LOST" if step["lost"] else "")
        self.save()

    # --- main thread ------------------------------------------------------------------------------
    def finish(self, final_frame: np.ndarray | None = None) -> list[dict]:
        self.q.put(None)
        self._worker.join(timeout=5)
        if final_frame is not None:
            cv2.imwrite(str(self.folder / "views/final.jpg"), final_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        self.save()
        return self.steps

    def save(self) -> None:
        (self.folder / "route.json").write_text(json.dumps({"steps": self.steps}, indent=1))
