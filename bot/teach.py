"""Teach-and-repeat: record a route Stephen plays (tools/record_route.py), for the bot to replay.

Each of his clicks becomes a step: button, client position, the automap fix after it (world px from
the waypoint arrival, on the Durance 2 canvas), and the view (saved as a jpg for view matching on
replay). Right-clicks are teleports, the left click at the end is the stairs. Clicks run on the
listener thread; frames are grabbed on a worker thread SETTLE s later, when the teleport has landed.
Stephen holds the right button to teleport (one press, ~10 casts): while it's held, the worker also
takes a step every HOLD_EVERY s at the cursor's current spot ("held": true). Without that, his 2026-10-29
Durance 2 recording kept one teleport per hold and the stairs click pointed nowhere.
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
HOLD_EVERY = 0.35  # s between steps while the right button is held (about one cast)


class RouteRecorder:
    def __init__(self, capture, odo, client_origin: tuple[int, int], folder: Path,
                 clock=time.monotonic, sleep=time.sleep, cursor=None, fresh_odo=None) -> None:
        self.capture, self.odo, self.folder = capture, odo, folder
        self.ox, self.oy = client_origin
        self.clock, self.sleep = clock, sleep
        self.cursor = cursor  # () -> screen (x, y) | None: samples while the right button is held
        self.fresh_odo = fresh_odo  # frame -> odometer: new_leg starts a fresh automap canvas
        self.leg = 0
        self.held = False
        self.last = 0.0  # clock of the last step's frame
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
            if button == "right":
                self.held = True

    def new_leg(self) -> None:
        """Stephen arrived in a new area: its automap is another canvas. In order with the clicks."""
        self.q.put("leg")

    def on_release(self, x: int, y: int, button: str) -> None:
        if button == "right":
            self.held = False

    # --- worker thread ----------------------------------------------------------------------------
    def _run(self) -> None:
        while True:
            try:
                item = self.q.get(timeout=0.05)
            except queue.Empty:
                item = self._held_sample()
                if item is None:
                    continue
            if item is None:
                return
            try:
                if item == "leg":
                    self._new_leg()
                else:
                    self._step(*item)
            except Exception:
                log.exception("recording a step failed")

    def _new_leg(self) -> None:
        if self.fresh_odo:
            self.odo.save(self.folder / f"canvas{self.leg}")
            self.odo = self.fresh_odo(self.capture.grab())
        self.leg += 1
        log.info("leg %d starts after step %d", self.leg, len(self.steps) - 1)

    def _held_sample(self):
        """A step at the cursor's spot if the right button is still held and a cast has passed."""
        if not (self.held and self.cursor) or self.clock() - self.last < HOLD_EVERY:
            return None
        pos = self.cursor()
        if pos is None:
            return None
        cx, cy = pos[0] - self.ox, pos[1] - self.oy
        if not (0 <= cx < 1280 and 0 <= cy < 720):
            return None
        return self.clock() - SETTLE, cx, cy, "right", True

    def _step(self, t: float, cx: int, cy: int, button: str, held: bool = False) -> None:
        wait = t + SETTLE - self.clock()
        if wait > 0:
            self.sleep(wait)
        frame = self.capture.grab()
        self.last = self.clock()
        expect = (cx - CENTER[0], cy - CENTER[1]) if button == "right" else None
        before = self.odo.pos.copy()
        self.odo.update(frame, expect=expect)
        i = len(self.steps)
        name = f"views/{i:03d}.jpg"
        cv2.imwrite(str(self.folder / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        step = {"i": i, "t": round(t - self.t0, 2), "button": button, "click": [cx, cy],
                "from": [round(float(v), 1) for v in before], "pos": [round(float(v), 1) for v in self.odo.pos],
                "resp": round(float(self.odo.resp), 3), "lost": bool(self.odo.lost), "view": name}
        if held:
            step["held"] = True
        if self.leg:
            step["leg"] = self.leg
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
