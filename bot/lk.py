"""M4/M5: Lower Kurast route -> open super chests -> pick up filtered loot.

The route is per-map data (maps/<name>/route.yaml). On arrival we check a fingerprint of the
waypoint view; a mismatch means the map seed changed and the route is stale (MapChanged).
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
import yaml

from .config import ROOT
from .controller import BotError, Controller
from .vision.labels import find_labels

log = logging.getLogger(__name__)

CENTER = (640, 330)  # character's screen position
TP_SETTLE = 0.45     # seconds per teleport (cast + landing)


class MapChanged(BotError):
    """Arrival view doesn't match the stored map fingerprint: route is stale."""


def load_route(name: str) -> dict:
    return yaml.safe_load((ROOT / "maps" / name / "route.yaml").read_text())


def check_fingerprint(bot: Controller, route: dict) -> None:
    fp = route["fingerprint"]
    if bot.find(fp["template"], region=fp["region"], threshold=fp["threshold"]) is None:
        bot.save_failure("map_fingerprint_mismatch")
        raise MapChanged("LK waypoint view doesn't match the stored map fingerprint")


def teleport(bot: Controller, dx: int, dy: int) -> None:
    bot.click(CENTER[0] + dx, CENTER[1] + dy, "right")
    bot.sleep(TP_SETTLE)


def _tooltip_near(bot: Controller, x: int, y: int) -> bool:
    """Hover (x, y); True if an object tooltip (dark box, light text) pops up above it."""
    bot.input.move(1270, 590)
    bot.sleep(0.12)
    base = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
    bot.input.move(x, y)
    bot.sleep(0.15)
    g = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
    y0, x0 = max(0, y - 90), max(0, x - 120)
    return (np.abs(g[y0:y, x0 : x + 120] - base[y0:y, x0 : x + 120]) > 60).mean() > 0.02


def open_chest(bot: Controller, x: int, y: int, radius: int = 220, step: int = 35) -> bool:
    """Open the chest at about (x, y). Teleport landings jitter, so if the exact point shows no
    tooltip, hover-scan outward in rings (nearest first) up to `radius`."""
    pts = [(x, y)]
    for r in range(step, radius + 1, step):
        ring = [(x + dx, y + dy) for dx in range(-r, r + 1, step) for dy in range(-r, r + 1, step)
                if max(abs(dx), abs(dy)) == r]
        pts += [(px, py) for px, py in ring if 20 < px < 1260 and 60 < py < 560]
    base = None
    for i, (px, py) in enumerate(pts):
        if i % 6 == 0:
            bot.check()
            bot.input.move(1270, 590)
            bot.sleep(0.12)
            base = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
        bot.input.move(px, py)
        bot.kill.sleep(0.09)
        g = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
        y0, x0 = max(0, py - 90), max(0, px - 120)
        if (np.abs(g[y0:py, x0 : px + 120] - base[y0:py, x0 : px + 120]) > 60).mean() > 0.02:
            if i:
                log.info("chest found at (%d, %d), %d px from expected", px, py, abs(px - x) + abs(py - y))
            bot.click(px, py)
            bot.wait_still(timeout=2.5, min_wait=0.6)
            return True
    bot.save_failure("chest_not_found")
    log.warning("no chest tooltip near (%d, %d)", x, y)
    return False


def _label_text_px(frame: np.ndarray, ignore) -> int:
    """Rough amount of label text on screen: bright pixels inside dark boxes."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    for ix, iy, iw, ih in ignore:
        g[iy : iy + ih, ix : ix + iw] = 0
    dark = cv2.erode((g < 30).astype(np.uint8), np.ones((3, 9), np.uint8))
    near_dark = cv2.dilate(dark, np.ones((9, 25), np.uint8)) > 0
    return int(((g > 150) & near_dark).sum())


def ensure_labels_on(bot: Controller) -> None:
    """Show Items is a toggle (Alt). Decide once per game which state shows labels."""
    if getattr(bot, "_labels_known", False):
        return
    ignore = bot.cfg["vision"]["label_ignore"]
    a = _label_text_px(bot.capture.grab(), ignore)
    bot.press(bot.cfg["hotkeys"]["show_items"])
    bot.sleep(0.3)
    b = _label_text_px(bot.capture.grab(), ignore)
    if b < a:  # we just turned them off; turn back on
        bot.press(bot.cfg["hotkeys"]["show_items"])
        bot.sleep(0.3)
    log.debug("label text before/after toggle: %d/%d", a, b)
    bot._labels_known = True


def loot(bot: Controller, max_picks: int = 8) -> list[str]:
    """Pick up every visible label of the configured kinds. Returns kinds picked."""
    ensure_labels_on(bot)
    kinds = {k: v for k, v in bot.cfg["vision"]["labels"].items() if k in bot.cfg["loot"]["pick"]}
    picked: list[str] = []
    for i in range(max_picks):
        bot.check()
        if i == 0 and bot.cfg.get("debug_loot_frames"):
            import time

            cv2.imwrite(str(Path(bot.cfg["paths"]["raw_frames"]) / f"loot_{time.strftime('%H%M%S')}.png"),
                        bot.frame)
        labels = find_labels(bot.frame, kinds, ignore=bot.cfg["vision"]["label_ignore"])
        if not labels:
            break
        lab = min(labels, key=lambda l: abs(l.center[0] - CENTER[0]) + abs(l.center[1] - CENTER[1]))
        log.info("pick %s label at %s", lab.kind, lab.center)
        bot.click(*lab.center)
        bot.wait_still(timeout=3, min_wait=0.5)
        picked.append(lab.kind)
    return picked


def run_route(bot: Controller, route: dict) -> dict:
    """From the LK waypoint: visit each target, open its chests, loot. Returns stats."""
    check_fingerprint(bot, route)
    stats = {"chests": 0, "picked": []}
    for t in route["targets"]:
        log.info("-> %s", t["name"])
        for dx, dy in t["hops"]:
            teleport(bot, dx, dy)
        bot.wait_still(timeout=1.5, min_wait=0.1)
        for cx, cy in t["chests"]:
            if open_chest(bot, cx, cy):
                stats["chests"] += 1
                stats["picked"] += loot(bot)
    return stats
