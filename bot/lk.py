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
TP_SETTLE = 0.2      # seconds per teleport (cast + landing); see nav.TP_SETTLE


class MapChanged(BotError):
    """Arrival view doesn't match the stored map fingerprint: route is stale."""


# Bonfire camp layout, as offsets from the bonfire (world px, measured at the east camp 2026-10-26
# and matching the west camp within ~25 px): where to stand, and where the chest is.
BONFIRE_LAYOUT = {
    "nw":      {"stand": (-421, -191), "chest": (-582, -281)},  # hut NW of the fire, near its door
    "nw_deep": {"stand": (-784, -373), "chest": (-957, -376)},  # same hut, far end
    "ne":      {"stand": (711, -281),  "chest": (850, -333)},   # hut NE of the fire
}


def bonfire_targets(camp: dict) -> list[dict]:
    """Expand a route `bonfires` entry into world targets (one per chest spot)."""
    bx, by = camp["world"]
    out = []
    for slot in camp.get("order", list(BONFIRE_LAYOUT)):
        lay = BONFIRE_LAYOUT[slot]
        out.append({"name": f"{camp['name']}_{slot}", "bonfire": [bx, by],
                    "world": [bx + lay["stand"][0], by + lay["stand"][1]],
                    "chests_world": [[bx + lay["chest"][0], by + lay["chest"][1]]]})
    return out


def load_route(name: str) -> dict:
    route = yaml.safe_load((ROOT / "maps" / name / "route.yaml").read_text())
    route.setdefault("name", name)
    route["targets"] = list(route.get("targets") or [])
    for camp in route.get("bonfires", []):
        route["targets"] += bonfire_targets(camp)
    return route


def fingerprint_match(frame: np.ndarray, template: np.ndarray, region, threshold: float,
                      half_threshold: float | None = None) -> bool:
    """Whole template, or its left or right half: the merc often stands on one brazier."""
    from .vision.screen import match_score

    if match_score(frame, template, region)[0] >= threshold:
        return True
    w = template.shape[1]
    half = threshold if half_threshold is None else half_threshold
    return any(match_score(frame, p, region)[0] >= half for p in (template[:, : w // 2], template[:, w // 2 :]))


def check_fingerprint(bot: Controller, route: dict) -> None:
    """Retries for ~2 s: the merc arriving next to us (with a glow) can cover the platform."""
    from .vision.screen import ASSETS

    fp = route["fingerprint"]
    tpl = cv2.imread(str(ASSETS / fp["template"]))
    for i in range(5):
        if i:
            bot.kill.sleep(0.5)
        bot.observe()
        if fingerprint_match(bot.frame, tpl, fp["region"], fp["threshold"], fp.get("half_threshold")):
            return
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


_CHEST_TMPLS: list | None = None


def _is_chest(frame: np.ndarray, box) -> bool:
    """Tooltip text says Chest / Locked Chest (templates in bot/assets/templates/tt_chest*.png).
    With no templates yet, accept anything and save the crop for labeling."""
    global _CHEST_TMPLS
    from .vision.screen import ASSETS

    bx, by, bw, bh = box
    crop = frame[by : by + bh, bx : bx + bw]
    if _CHEST_TMPLS is None:
        _CHEST_TMPLS = [cv2.imread(str(p)) for p in sorted(ASSETS.glob("tt_chest*.png"))]
    if not _CHEST_TMPLS:
        import time

        d = ROOT / "fixtures" / "raw"
        cv2.imwrite(str(d / f"tooltip_{time.strftime('%H%M%S')}_{bx}_{by}.png"), crop)
        return True
    for t in _CHEST_TMPLS:
        if t.shape[0] <= crop.shape[0] + 2 and t.shape[1] <= crop.shape[1] + 2:
            c = cv2.copyMakeBorder(crop, 2, 2, 2, 2, cv2.BORDER_REPLICATE)
            if cv2.minMaxLoc(cv2.matchTemplate(c, t, cv2.TM_CCOEFF_NORMED))[1] > 0.8:
                return True  # "Chest" also matches inside "Locked Chest"
    return False


LOCKED_MIN_W = 100  # tooltip box px, measured live: "Chest" 59-65, "Locked Chest" 134-140


def open_chest(bot: Controller, x: int, y: int, radius: int = 220, step: int = 35) -> tuple[int, int] | None:
    """Open the chest at about (x, y). Teleport landings jitter, so if the exact point shows no
    tooltip, hover-scan outward in rings (nearest first) up to `radius`. Returns where it was found."""
    pts = [(x, y)]
    for r in range(step, radius + 1, step):
        pts += [(x + dx, y + dy) for dx in range(-r, r + 1, step) for dy in range(-r, r + 1, step)
                if max(abs(dx), abs(dy)) == r]
    pts = [(px, py) for px, py in pts if 20 < px < 1260 and 60 < py < 560]
    if not pts:
        log.warning("chest point (%d, %d) is off screen: odometry is off", x, y)
        return None
    from .vision.tooltip import find_tooltip

    for i, (px, py) in enumerate(pts):
        bot.check()  # every point: bursts from champion packs kill in about a second
        bot.input.move(px, py)
        bot.kill.sleep(0.09)
        f = bot.capture.grab()
        box = find_tooltip(f, px, py)
        if box is not None and not _is_chest(f, box):
            continue
        if box is not None:
            if i:
                log.info("chest found at (%d, %d), %d px from expected", px, py, abs(px - x) + abs(py - y))
            log.debug("chest tooltip %dx%d", box[2], box[3])
            if box[2] > LOCKED_MIN_W:  # "Locked Chest" tooltip: opening it uses a key
                bot.keys_used = getattr(bot, "keys_used", 0) + 1
            bot.click(px, py)
            bot.wait_still(timeout=2.5, min_wait=0.6)
            return px, py
    bot.save_failure("chest_not_found")
    log.warning("no chest tooltip near (%d, %d)", x, y)
    return None


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
        if lab.kind != "white":  # keep evidence of every valuable pick for review
            import time

            p = ROOT / "fixtures" / "raw" / f"pick_{lab.kind}_{time.strftime('%m%d-%H%M%S')}.png"
            img = bot.frame.copy()
            cv2.rectangle(img, (lab.x, lab.y), (lab.x + lab.w, lab.y + lab.h), (0, 255, 255), 1)
            cv2.imwrite(str(p), img)
        bot.click(*lab.center)
        bot.wait_still(timeout=3, min_wait=0.5)
        picked.append(lab.kind)
    return picked


REANCHOR_AFTER = 1500  # px of travel before odometry drift is worth a landmark fix
LEARN_KEEP = 9         # found-chest samples kept per chest (median is used)


def _learned_path(route: dict) -> Path:
    return ROOT / "maps" / route["name"] / "learned.json"


def load_learned(route: dict) -> dict:
    """Chest world positions where the search actually found them: {target: {index: [[x, y], ...]}}."""
    import json

    p = _learned_path(route)
    return json.loads(p.read_text()) if p.exists() else {}


def chest_world(t: dict, i: int, learned: dict) -> tuple[float, float]:
    """Median of learned positions for chest i of target t, else the scouted one."""
    samples = learned.get(t["name"], {}).get(str(i))
    if samples:
        return tuple(np.median(np.asarray(samples, float), axis=0))
    return tuple(t["chests_world"][i])


LEARN_MAX_OFF = 150  # px from the scouted spot; farther finds are probably a different object


def learn_chest(route: dict, learned: dict, t: dict, i: int, world) -> None:
    import json

    if np.hypot(*(np.asarray(world, float) - t["chests_world"][i])) > LEARN_MAX_OFF:
        log.info("%s chest %d found %s, too far from the scouted spot to learn", t["name"], i, np.round(world).tolist())
        return
    lst = learned.setdefault(t["name"], {}).setdefault(str(i), [])
    lst.append([round(float(world[0])), round(float(world[1]))])
    del lst[:-LEARN_KEEP]
    _learned_path(route).write_text(json.dumps(learned, indent=1))


def _in_view(a, b) -> bool:
    """Is world point b on screen when standing at world point a?"""
    return abs(b[0] - a[0]) < 560 and abs(b[1] - a[1]) < 230


def run_route(bot: Controller, route: dict) -> dict:
    """From the LK waypoint: visit each target, open its chests, loot. Returns stats.

    A target is either `hops` (relative teleports) + `chests` (screen coords after the last hop),
    or `world` (teleport_to target, world coords from the WP arrival view) + `chests_world`.
    Odometry runs throughout, so both kinds can be mixed in one route.

    Get in, open, get out: no fighting unless a target sets `fight: true`. Bonfire targets re-anchor
    odometry only when it's lost or has drifted a while; if the bonfire isn't visible from the stand
    point, it's visited first. Where chests were actually found is learned (maps/<route>/learned.json).
    """
    from .nav import CENTER as C, Odometer, bonfire_stand, fight, hop, reanchor, search_bonfire, teleport_to, world_to_screen

    check_fingerprint(bot, route)
    learned = load_learned(route)
    stats = {"chests": 0, "picked": []}
    odo = Odometer(bot.capture.grab())
    unfound = set()  # bonfires a lost-odometry search couldn't find this run
    for t in route["targets"]:
        log.info("-> %s", t["name"])
        if "world" in t:
            bf = t.get("bonfire")
            if bf is not None and tuple(bf) in unfound:
                stats.setdefault("skipped", []).append(t["name"])
                continue
            leg = float(np.hypot(*(np.asarray(t["world"], float) - odo.pos)))  # the leg ahead drifts too
            need_anchor = bf is not None and (odo.lost or odo.since_anchor + leg > REANCHOR_AFTER)
            if need_anchor and not _in_view(t["world"], bf):
                teleport_to(bot, odo, bonfire_stand(bf), tol=120)  # bonfire first, then the stand point
                need_anchor = not reanchor(bot, odo, bf)
            if not teleport_to(bot, odo, t["world"]):
                gap = float(np.hypot(*(np.asarray(t["world"], float) - odo.pos)))
                if gap > 200:
                    continue
                log.info("%s: %d px from the stand point; searching anyway", t["name"], gap)
            if t.get("fight", False):
                fight(bot, odo=odo)
            need_anchor = bf is not None and (need_anchor or odo.lost)  # lost on the way: a blind chest
            if need_anchor:                                              # scan costs ~30 s for nothing
                if not reanchor(bot, odo, bf) and odo.lost:
                    log.warning("%s: odometry lost and no bonfire in view -> searching", t["name"])
                    if not search_bonfire(bot, odo, bf):
                        unfound.add(tuple(bf))  # don't search again for this camp's other chests
                    if odo.lost or not teleport_to(bot, odo, t["world"]):
                        stats.setdefault("skipped", []).append(t["name"])
                        continue
                    stats["recovered"] = stats.get("recovered", 0) + 1
                elif not teleport_to(bot, odo, t["world"]):  # the fix may have moved the stand point
                    continue                                 # (cheap when it didn't)
            points = [world_to_screen(odo, *chest_world(t, i, learned)) for i in range(len(t["chests_world"]))]
        else:
            for dx, dy in t["hops"]:
                hop(bot, odo, dx, dy)
            points = [tuple(c) for c in t["chests"]]
        bot.wait_still(timeout=1.5, min_wait=0.1)
        odo.update(bot.capture.grab())
        if "world" in t:  # the settle may have moved the view a little
            points = [world_to_screen(odo, *chest_world(t, i, learned)) for i in range(len(points))]
        for i, (cx, cy) in enumerate(points):
            found = open_chest(bot, cx, cy)
            if found:
                if "world" in t and not odo.lost:
                    learn_chest(route, learned, t, i, (odo.pos[0] + found[0] - C[0], odo.pos[1] + found[1] - C[1]))
                stats["chests"] += 1
                stats["picked"] += loot(bot)
                odo.update(bot.capture.grab())  # picking items walks us around
    return stats
