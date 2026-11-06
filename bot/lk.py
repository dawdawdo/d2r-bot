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
from .controller import BotError, Controller, Danger
from .vision.labels import find_labels

log = logging.getLogger(__name__)

CENTER = (640, 330)  # character's screen position
TP_SETTLE = 0.2      # seconds per teleport (cast + landing); see nav.TP_SETTLE


class TerrorZone(BotError):
    """Lower Kurast is this hour's Terror Zone: monsters far stronger (2026-11-02 10:00: 4 chickens in 7 runs)."""


_TERROR: list = []


def _terror_mask(img: np.ndarray) -> np.ndarray:
    i = img.astype(np.int16)
    b, g, r = i[..., 0], i[..., 1], i[..., 2]
    return ((b > 140) & (r > 100) & (g < b - 30)).astype(np.float32)  # the banner's purple letters


def terrorized(frame: np.ndarray) -> bool:
    """The purple "Terrorized" line under "Entering Lower Kurast" (shown for a few seconds on arrival)."""
    if not _TERROR:
        _TERROR.append(_terror_mask(cv2.imread(str(ROOT / "bot" / "assets" / "templates" / "terrorized.png"))))
    reg = _terror_mask(frame[150:260, 440:840])
    if reg.sum() < 0.3 * _TERROR[0].sum():
        return False
    return float(cv2.matchTemplate(reg, _TERROR[0], cv2.TM_CCORR_NORMED).max()) >= 0.7


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


def _fp_template(route: dict) -> np.ndarray:
    """The fingerprint template: maps/<route>/ (learned maps) or bot/assets/templates/."""
    from .vision.screen import ASSETS

    name = route["fingerprint"]["template"]
    p = ROOT / "maps" / route.get("name", "") / name
    return cv2.imread(str(p if p.exists() else ASSETS / name))


def fingerprint_ok(bot: Controller, route: dict) -> bool:
    """One quick look: does the view match the LK waypoint fingerprint? (Skips the slower automap
    area-name check on arrival; check_fingerprint still retries before the route.)"""
    from .vision.screen import ASSETS

    fp = route["fingerprint"]
    tpl = _fp_template(route)
    bot.observe()
    return bool(fingerprint_match(bot.frame, tpl, fp["region"], fp["threshold"], fp.get("half_threshold")))


WP_CLICK = (78, 42)  # fingerprint template (160x60) top-left -> platform center (live 2026-10-27: +-45 px in x
                    # opens the menu even with us standing on it; the front step, +23 px lower, walks away)
WP_SEARCH = (100, 40, 1080, 550)
WP_AT = (560, 330)  # fingerprint top-left when standing on the platform (the arrival view)


def _find_lk_wp(bot: Controller, route: dict) -> tuple[int, int] | None:
    """Top-left of the LK waypoint fingerprint in the view: the whole template, else its better half
    (the merc on a brazier)."""
    from .vision.screen import match_score

    tpl = _fp_template(route)
    fp = route["fingerprint"]
    bot.observe()
    score, loc = match_score(bot.frame, tpl, WP_SEARCH)
    if score >= fp["threshold"]:
        return loc
    w = tpl.shape[1]
    (score, (x, y)), dx = max([(match_score(bot.frame, tpl[:, : w // 2], WP_SEARCH), 0),
                               (match_score(bot.frame, tpl[:, w // 2 :], WP_SEARCH), w // 2)], key=lambda m: m[0][0])
    return (x - dx, y) if score >= fp.get("half_threshold", 0.5) else None


def leave_to_act4(bot: Controller, route: dict, odo) -> bool:
    """End of the route: teleport back to the LK waypoint, take it to the Pandemonium Fortress, so the
    next game spawns next to the A4 waypoint. False if anything doesn't work out (the caller then just
    saves & exits here, as before). Safety exceptions (chicken etc.) propagate."""
    if not leave_via_wp(bot, route, odo, "wp_tab_act4", "wp_town"):
        return False
    bot.guard(False)  # in town
    return True


def leave_via_wp(bot: Controller, route: dict, odo, tab: str, dest: str) -> bool:
    """Teleport back to the LK waypoint and take it to `dest` on the `tab` waypoint tab (Act 4 town, or
    the next task's waypoint). False if that doesn't work out."""
    from .nav import HOP_GAIN, teleport_to
    from .town import wp_travel

    t0 = bot.clock()
    if not teleport_to(bot, odo, (0, 0), tol=60, quiet=True):
        log.info("leaving LK: couldn't get back to the LK waypoint")
        return False
    t1 = bot.clock()
    for attempt in range(3):
        loc = _find_lk_wp(bot, route)
        if loc is None:
            bot.save_failure("lk_wp_not_found")
            log.info("leaving LK: LK waypoint not in view")
            return False
        dx, dy = loc[0] - WP_AT[0], loc[1] - WP_AT[1]
        if np.hypot(dx, dy) > 45:  # odometry drifted (2026-10-27: 230 px off): hop onto the platform first
            log.info("leaving LK: waypoint %d px off, hopping onto it", np.hypot(dx, dy))
            teleport(bot, round(dx / HOP_GAIN), round(dy / HOP_GAIN))
            continue
        bot.click(loc[0] + WP_CLICK[0], loc[1] + WP_CLICK[1])
        try:
            bot.wait_for("wp_menu", 3)
            break
        except BotError:
            log.info("leaving LK: waypoint menu didn't open (attempt %d)", attempt + 1)
    else:
        return False
    t2 = bot.clock()
    wp_travel(bot, tab, dest)
    log.info("LK waypoint -> %s (teleport %.1fs, wp menu %.1fs, travel %.1fs)",
             dest, t1 - t0, t2 - t1, bot.clock() - t2)
    return True


def check_fingerprint(bot: Controller, route: dict) -> None:
    """Retries for ~2 s: the merc arriving next to us (with a glow) can cover the platform."""
    from .vision.screen import ASSETS

    fp = route["fingerprint"]
    tpl = _fp_template(route)
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


SCAN_JUMP = 80  # px the view may move during a chest hover scan before we call it a jump


def open_chest(bot: Controller, x: int, y: int, radius: int = 220, step: int = 35,
               click: bool = True, odo=None) -> tuple[int, int] | None:
    """Open the chest at about (x, y). Teleport landings jitter, so if the exact point shows no
    tooltip, hover-scan outward in rings (nearest first) up to `radius`. Returns where it was found.
    `click=False` only looks (map learning: is there a chest here?). With `odo`, the scan stops early
    when the view jumps (teleport-when-struck moved us; 2026-10-27 a scan ran 28 s for nothing)."""
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
        if odo is not None and i and i % 10 == 0:
            dx, dy = odo.update(bot.frame)
            if np.hypot(dx, dy) > SCAN_JUMP:
                log.info("view jumped (%d, %d) during the chest scan", dx, dy)
                bot.scan_jumped = True
                return None
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
            if not click:
                return px, py
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


LABEL_DECIDE_PX = 60  # label-text pixels that must differ between Alt states to tell which one shows labels


def ensure_labels_on(bot: Controller) -> None:
    """Show Items is a toggle (Alt). Decide once per game which state shows labels."""
    if getattr(bot, "_labels_known", False):
        return
    ignore = bot.cfg["vision"]["label_ignore"]
    a = _label_text_px(bot.capture.grab(), ignore)
    bot.press(bot.cfg["hotkeys"]["show_items"])
    bot.sleep(0.3)
    b = _label_text_px(bot.capture.grab(), ignore)
    log.debug("label text before/after toggle: %d/%d", a, b)
    if abs(a - b) < LABEL_DECIDE_PX:
        # nothing on the ground to tell by: undo the toggle and decide at the next loot. (Keeping it flipped
        # here hid the labels for whole games, Stephen 2026-11-02: "the loot isn't showing on the ground")
        bot.press(bot.cfg["hotkeys"]["show_items"])
        bot.sleep(0.3)
        return
    if b < a:  # we just turned them off; turn back on
        bot.press(bot.cfg["hotkeys"]["show_items"])
        bot.sleep(0.3)
    log.info("item labels: %s (label text %d -> %d)", "were off, now on" if b > a else "on", a, b)
    bot._labels_known = True


def _want_supply(bot: Controller, word: str | None) -> bool:
    """Keys while below a full stack; rejuvs always: into the belt while it has an empty slot, else into the
    inventory and on to the stash (Materials tab), where restocks take them from. Stephen: sustain from chest
    drops, no buying (2026-10-26); the stash supply should grow (2026-10-31: picks ~= drinks, ~16 per 100 runs,
    so leaving spares on the ground meant no reserve). A stash stack holds 99."""
    if word == "key":
        left = getattr(bot, "keys_left", None)  # a pickup can be a whole stack: wait until we're low
        return left is None or left < bot.cfg["town"].get("keys_pick_below", bot.cfg["town"]["keys_full"])
    if word != "rejuv":
        return False
    from . import state
    from .vision.orbs import belt_slots

    if not all(belt_slots(bot.frame, bot.cfg["vision"]["belt"])):
        return True
    # spares for the stash: off since Stephen 2026-11-02 ("stashing tons of potions ... no need for that");
    # when on, only while the stash stack has room (99 max; logs/state.json, set by the stowaway)
    return bool(bot.cfg["loot"].get("rejuv_spares")) and not state.load().get("rejuv_stash_full")


def _sig(lab) -> tuple:
    return lab.kind, lab.w // 4, lab.h // 4


def loot(bot: Controller, max_picks: int = 10, take_all: bool = False) -> list[str]:
    """Pick up every visible label of the configured kinds, plus keys and rejuvs we need
    (white labels, told apart from gold by their first word). Returns what was picked.
    take_all (boss drops): every label color, no charm/supply check: the filter already hid the junk,
    and boss-only items (essences, the Warlock release's ancients' statues) have colors we haven't seen."""
    from .vision.labels import is_charm, white_word
    from .vision.orbs import belt_slots

    ensure_labels_on(bot)
    labels_cfg = bot.cfg["vision"]["labels"]
    kinds = {k: v for k, v in labels_cfg.items() if take_all or k in bot.cfg["loot"]["pick"]}
    supplies = bot.cfg["loot"].get("supplies", [])
    if supplies and not take_all:
        kinds.setdefault("white", labels_cfg["white"])
    picked: list[str] = []
    tried: dict[tuple[int, int], int] = {}
    rescanned = False
    for i in range(max_picks):
        bot.check()
        if (i == 0 or (i == 1 and rescanned)) and bot.cfg.get("debug_loot_frames"):
            import time

            cv2.imwrite(str(Path(bot.cfg["paths"]["raw_frames"]) / f"loot_{time.strftime('%H%M%S')}{'_re' if i else ''}.png"),
                        bot.frame)
        found = []
        ignore = bot.cfg["vision"]["label_ignore"]
        if take_all or bot.cfg["loot"].get("pick_white_other"):
            # white text that isn't an item: a hovered monster's name bar + mods line at the top centre,
            # the merc's name under his portrait
            ignore = [*ignore, [300, 0, 680, 60], [0, 0, 110, 90]]
        labs = find_labels(bot.frame, kinds, ignore=ignore)
        # "1550 Gold" shows as two labels: the amount, then the word (51 px); neither is an item to pick here
        golds = [g for g in labs if g.kind == "white" and white_word(bot.frame, g) == "gold"]
        gold_amounts = {id(a) for a in labs for g in golds
                        if a is not g and abs(a.y - g.y) <= 3 and 0 <= g.x - (a.x + a.w) <= 12}
        for lab in labs:
            if lab in golds or id(lab) in gold_amounts:
                continue
            what = lab.kind
            if take_all:
                if lab.kind == "white":
                    what = white_word(bot.frame, lab) or "white"
                    if what in ("key", "rejuv") and not _want_supply(bot, what):
                        continue
            if lab.kind == "white" and not take_all:
                what = white_word(bot.frame, lab)
                if what is None and bot.cfg["loot"].get("pick_white_other"):
                    # the filter hides gold and most white gear: a white label that's no key / rejuv is a
                    # flawless or perfect gem or skull, or one of Stephen's runeword bases
                    what = "gem"
                elif what not in supplies or not _want_supply(bot, what):
                    continue
            if lab.kind == "magic":  # take_all too: blue jewels show (the jewel rule has no rarity)
                if not is_charm(bot.frame, lab):
                    continue
                what = "charm"
            if tried.get((lab.center[0] // 10, lab.center[1] // 10), 0) >= 2 or tried.get(_sig(lab), 0) >= 2:
                continue  # still there after two clicks: can't pick it up (full, or not an item)
            found.append((what, lab))
        if not found:
            if i == 0 and not rescanned and _label_text_px(bot.frame, bot.cfg["vision"]["label_ignore"]) < 100:
                # no label at all yet (drops still landing; labels come after): one more look. A chest that
                # shows gold labels (130-3400 px, 24 chests 2026-11-02) has landed: no wait
                rescanned = True
                bot.sleep(0.7)
                bot.frame = bot.capture.grab()
                continue
            break
        what, lab = min(found, key=lambda f: abs(f[1].center[0] - CENTER[0]) + abs(f[1].center[1] - CENTER[1]))
        log.info("pick %s label at %s", what, lab.center)
        if lab.kind != "white":  # keep evidence of every valuable pick for review
            import time

            # clean frame (a drawn box spoils it as a test fixture); the label box is in the name
            name = f"pick_{lab.kind}_{time.strftime('%m%d-%H%M%S')}_{lab.x}_{lab.y}_{lab.w}_{lab.h}.png"
            cv2.imwrite(str(ROOT / "fixtures" / "raw" / name), bot.frame)
        cell = (lab.center[0] // 10, lab.center[1] // 10)
        tried[cell] = tried.get(cell, 0) + 1
        # by kind + text width too: the label moves as she walks to it (no room: 9 clicks on 2 items, 2026-11-02)
        tried[_sig(lab)] = tried.get(_sig(lab), 0) + 1
        bot.click(*lab.center)
        bot.wait_still(timeout=3, min_wait=0.5)
        if what == "rejuv" and all(belt_slots(bot.frame, bot.cfg["vision"]["belt"])):
            what = "rejuv_spare"  # belt full: it goes to the inventory, so stash it after this run
        if what == "key" and getattr(bot, "keys_left", None) is not None:
            bot.keys_left += 1
        picked.append(what)
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


LEARN_MAX_OFF = 150  # px from the scouted spot; farther finds are probably a different object (200 let east_nw learn
                     # a second object 153 px away and the median drifted: 3 s -> 20 s)


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


def run_route(bot: Controller, route: dict, end=None) -> dict:
    """From the LK waypoint: visit each target, open its chests, loot. Returns stats.

    A target is either `hops` (relative teleports) + `chests` (screen coords after the last hop),
    or `world` (teleport_to target, world coords from the WP arrival view) + `chests_world`.
    Odometry runs throughout, so both kinds can be mixed in one route.

    Get in, open, get out: no fighting unless a target sets `fight: true`. Bonfire targets re-anchor
    odometry only when it's lost or has drifted a while; if the bonfire isn't visible from the stand
    point, it's visited first. Where chests were actually found is learned (maps/<route>/learned.json).
    """
    from .nav import Odometer

    check_fingerprint(bot, route)
    learned = load_learned(route)
    stats = {"chests": 0, "picked": []}
    odo = Odometer(bot.capture.grab())
    unfound = set()  # bonfires a lost-odometry search couldn't find this run
    bot.flee_ok = True
    try:
        for t in route["targets"]:
            bf = t.get("bonfire")
            if bf is not None and tuple(bf) in unfound:
                stats.setdefault("skipped", []).append(t["name"])
                continue
            try:
                _visit(bot, t, odo, learned, route, stats, unfound)
            except Danger as e:  # mana burned out at a camp: give up its chests, not the whole run
                log.warning("%s: %s -> fleeing to the next camp", t["name"], e)
                stats["fled"] = stats.get("fled", 0) + 1
                odo.lost = True  # cut off mid-hop: re-anchor at the next camp
                if bf is not None:
                    unfound.add(tuple(bf))
    finally:
        bot.flee_ok = False
    if end is not None:  # e.g. back to the waypoint (`end(odo, stats)`)
        end(odo, stats)
    return stats


FRESH_ANCHOR = 1000  # px travelled since a bonfire fix (stand points are up to ~800 px from the fire): chests
                    # are then within ~35 px of their learned spot
                    # (2026-10-27), so scan 105 px, not 220 (25 s when a monster pack hides the chest)


def clear_spot(bot: Controller, x: int, y: int, casts: int = 3) -> None:
    """The attack skill at a screen point (a pack standing on a chest hides its tooltip), then Teleport back."""
    sk = bot.cfg["hotkeys"]["skills"]
    bot.press(sk[bot.cfg["hotkeys"]["attack"]])
    try:
        for _ in range(casts):
            bot.click(x, y, "right", hover=0)
            bot.sleep(0.45)
    finally:
        bot.press(sk["teleport"])


def _visit(bot: Controller, t: dict, odo, learned: dict, route: dict, stats: dict, unfound: set) -> None:
    """One route target: get there (re-anchoring as needed), open its chests, loot."""
    from .nav import CENTER as C, bonfire_stand, fight, hop, reanchor, search_bonfire, teleport_to, world_to_screen

    log.info("-> %s", t["name"])
    if "world" in t:
        bf = t.get("bonfire")
        if bf is not None and tuple(bf) in unfound:
            stats.setdefault("skipped", []).append(t["name"])
            return
        leg = float(np.hypot(*(np.asarray(t["world"], float) - odo.pos)))  # the leg ahead drifts too
        need_anchor = bf is not None and (odo.lost or odo.since_anchor + leg > REANCHOR_AFTER)
        if need_anchor and not _in_view(t["world"], bf):
            teleport_to(bot, odo, bonfire_stand(bf), tol=120)  # bonfire first, then the stand point
            need_anchor = not reanchor(bot, odo, bf)
        if not teleport_to(bot, odo, t["world"]):
            gap = float(np.hypot(*(np.asarray(t["world"], float) - odo.pos)))
            if gap > 200:
                return
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
                    return
                stats["recovered"] = stats.get("recovered", 0) + 1
            elif not teleport_to(bot, odo, t["world"]):  # the fix may have moved the stand point
                return                                 # (cheap when it didn't)
        points = [world_to_screen(odo, *chest_world(t, i, learned)) for i in range(len(t["chests_world"]))]
    else:
        for dx, dy in t["hops"]:
            hop(bot, odo, dx, dy)
        points = [tuple(c) for c in t["chests"]]
    bot.wait_still(timeout=1.0, settle=1, poll=0.05, min_wait=0.0)  # teleports already settle 0.2 s
    odo.update(bot.capture.grab())
    if "world" in t:  # the settle may have moved the view a little
        points = [world_to_screen(odo, *chest_world(t, i, learned)) for i in range(len(points))]
    for i, (cx, cy) in enumerate(points):
        fresh = "world" in t and not odo.lost and odo.since_anchor < FRESH_ANCHOR
        bot.scan_jumped = False
        found = open_chest(bot, cx, cy, odo=odo, radius=105 if fresh else 220)
        if not found and bot.scan_jumped and "world" in t:  # teleport-when-struck: go back, try once more
            bf = t.get("bonfire")
            if odo.lost and bf is not None:
                reanchor(bot, odo, bf)
            if not odo.lost and teleport_to(bot, odo, t["world"]):
                log.info("%s: back at the stand point after the jump; scanning again", t["name"])
                odo.update(bot.capture.grab())
                cx, cy = world_to_screen(odo, *chest_world(t, i, learned))
                found = open_chest(bot, cx, cy, odo=odo, radius=105)
        if not found and fresh and not odo.lost:  # we know where it is: monsters standing on it?
            log.info("%s: chest hidden at (%d, %d); attacking, then look again", t["name"], cx, cy)
            clear_spot(bot, cx, cy)
            odo.update(bot.capture.grab())
            cx, cy = world_to_screen(odo, *chest_world(t, i, learned))
            found = open_chest(bot, cx, cy, odo=odo, radius=70)
        if found and "world" in t and not odo.lost:  # before the update below: opening walks us to it
            learn_chest(route, learned, t, i, (odo.pos[0] + found[0] - C[0], odo.pos[1] + found[1] - C[1]))
        odo.update(bot.capture.grab())  # a when-struck teleport during the scan moves us too
        if not found and "world" in t and not odo.lost:
            log.info("chest missing: position suspect, re-anchor at the next target")
            odo.lost = True  # (2026-10-26: a 470 px jump in a scan cost the rest of the run)
        if found:
            stats["chests"] += 1
            stats["picked"] += loot(bot)
            odo.update(bot.capture.grab())  # picking items walks us around
