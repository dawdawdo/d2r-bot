"""M3: Act 3 town (Kurast Docks) -> waypoint -> Lower Kurast.

New games always start at the same spot by Meshif's boat, and the town layout is fixed,
so we walk a recorded route (config town.route) and then locate the waypoint by template.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from . import supplies
from .config import ROOT
from .controller import BotError, Controller
from .vision.screen import ASSETS

log = logging.getLogger(__name__)


def _view_moved(a: np.ndarray, b: np.ndarray) -> bool:
    return float(np.abs(a[:560].astype(np.int16) - b[:560]).mean()) > 4


def walk_route(bot: Controller, route: list, retries: int = 2) -> list[tuple[float, float]]:
    """Click each leg in turn. If the view didn't move (click swallowed right after the game
    loads, or a wandering NPC was in the way), click the leg again. Returns each leg's view
    displacement measured by odometry (logged; used to calibrate chained walking)."""
    from .nav import Odometer

    odo = Odometer(bot.capture.grab())
    disps = []
    for i, (x, y) in enumerate(route):
        for attempt in range(retries + 1):
            before = bot.capture.grab()
            start = odo.pos.copy()
            odo.update(before)
            bot.click(x, y)
            if not _walk_settle(bot, odo):
                log.info("leg %d: view still moving after timeout", i)
            if _view_moved(before, bot.capture.grab()):
                break
            log.info("leg %d: didn't move (attempt %d), clicking again", i, attempt + 1)
            bot.kill.sleep(0.5)
        disps.append(tuple(float(v) for v in (odo.pos - start).round(1)))
    log.info("town walk legs %s%s", disps, " (odometry lost)" if odo.lost else "")
    return disps


WALK_GAIN = (1.04, 1.18)  # view displacement per px of click offset (live legs 2026-10-26; cf. nav.HOP_GAIN)
WALK_LEAD = 45           # px before a leg's end to click the next one (60 once cut the temple corner into a wall)
WALK_NEAR = 150          # stalled this close to a leg's end (a wall the recorded walk didn't meet): next leg
ESCAPES = [(-200, 0), (0, 150), (0, -150), (200, 0), (-150, 120), (150, -120)]
WALK_BOX = (30, 1250, 50, 550)  # clickable part of the view (x0, x1, y0, y1): not the HUD or the edges


def walk_chain(bot: Controller, route: list, disps: list, timeout: float = 30) -> int | None:
    """Walk the recorded legs without stopping: track the view by odometry and click the next leg's
    end (world = cumulative recorded displacements) when the current one is WALK_LEAD px away.
    Re-clicks when the view stalls (swallowed click, NPC in the way). Returns None when done, else the
    leg it gave up on (odometry lost, stuck): the caller walks the remaining legs one by one."""
    from .nav import CENTER, Odometer

    targets = np.cumsum(np.asarray(disps, float), axis=0)
    gain = np.asarray(WALK_GAIN)
    odo = Odometer(bot.capture.grab())

    def click_toward(t) -> None:
        x, y = np.asarray(CENTER, float) + (t - odo.pos) / gain
        x0, x1, y0, y1 = WALK_BOX
        bot.click(int(min(max(x, x0), x1)), int(min(max(y, y0), y1)))

    bot.click(*route[0])
    k, t0, stall_since, stalls, calm = 0, bot.clock(), bot.clock(), 0, 0
    while bot.clock() - t0 < timeout:
        bot.kill.sleep(0.03)
        f = bot.capture.grab()
        bot._guard_frame(f)
        dx, dy = odo.update(f)
        if odo.lost:
            log.info("chained walk: odometry lost at leg %d", k)
            return k
        moving = abs(dx) >= 1.5 or abs(dy) >= 1.5
        calm = 0 if moving else calm + 1
        rem = float(np.hypot(*(targets[k] - odo.pos)))
        last = k == len(targets) - 1
        if last and calm >= 3 and rem < 120:
            log.info("chained walk done in %.1fs, %.0f px from the recorded end", bot.clock() - t0, rem)
            return None
        if not last and rem < WALK_LEAD:
            k += 1
            click_toward(targets[k])
            stall_since = bot.clock()
            continue
        if moving:
            stall_since = bot.clock()
        elif bot.clock() - stall_since > 0.4 and not last and rem < WALK_NEAR:
            k += 1
            click_toward(targets[k])
            stall_since = bot.clock()
        elif bot.clock() - stall_since > 0.4:
            stalls += 1
            if stalls > 2 * len(ESCAPES) + 1:
                log.info("chained walk: stuck at leg %d (%.0f px to go)", k, rem)
                return k
            if stalls % 2:  # boxed in (2026-10-26: temple stairs, merc + NPC in the gap): step out, retry
                back = targets[k - 2] if k >= 2 else np.zeros(2)  # back along the way we came first
                esc = [back] + [odo.pos + np.asarray(d, float) for d in ESCAPES]
                log.info("chained walk: stalled at leg %d, escape %d", k, stalls // 2)
                bot.frame = f
                bot.save_failure(f"walk_stall_leg{k}_{stalls // 2}")
                click_toward(esc[stalls // 2])
                bot.kill.sleep(0.4)
            else:
                click_toward(targets[k])
            stall_since = bot.clock()
    log.info("chained walk: timeout at leg %d", k)
    return k


def _walk_settle(bot: Controller, odo, timeout: float = 6, min_wait: float = 0.2, poll: float = 0.05) -> bool:
    """Track the walk by odometry until the view stops (3 polls without movement)."""
    bot.kill.sleep(min_wait)
    deadline = bot.clock() + timeout
    calm = 0
    while bot.clock() < deadline:
        f = bot.capture.grab()
        bot._guard_frame(f)
        dx, dy = odo.update(f)
        calm = calm + 1 if abs(dx) < 1.5 and abs(dy) < 1.5 else 0
        if calm >= 3:
            return True
        bot.kill.sleep(poll)
    return False


ROUTE_END = ASSETS / "town_route_end.png"  # the view where the town route normally ends (saved on
                                           # the first clean WP open); corrects a walk an NPC cut short
ROUTE_END_TOL = 60  # px


def route_end_offset(ref: np.ndarray, frame: np.ndarray) -> tuple[float, float] | None:
    """Where the reference view's features are in `frame`, relative to the reference (phase
    correlation, as LK odometry). None if the views don't overlap enough to tell."""
    from .nav import MIN_RESPONSE, _odo_window, _small

    a, b = _small(ref), _small(frame)
    (dx, dy), resp = cv2.phaseCorrelate(a, b, _odo_window(a.shape))
    return (dx * 2, dy * 2) if resp >= MIN_RESPONSE else None


def fix_route_end(bot: Controller) -> None:
    """2026-10-26: an NPC cut the last leg short and the WP was off screen. Walk the difference."""
    from .nav import CENTER

    frame = bot.capture.grab()
    if not ROUTE_END.exists() or find_town_wp(bot, frame, bot.cfg["town"], quiet=True) is not None:
        return  # WP in view: good enough (without a stash visit we stop ~(160, 110) px short of the reference)
    off = route_end_offset(cv2.imread(str(ROUTE_END)), frame)
    if off is None or np.hypot(*off) < ROUTE_END_TOL:
        return
    log.info("town route ended %s px off; walking the difference", np.round(off).tolist())
    bot.click(int(CENTER[0] + off[0]), int(CENTER[1] + off[1]))
    bot.wait_still(timeout=4, settle=1, poll=0.1, min_wait=0.2)


def find_town_wp(bot: Controller, frame: np.ndarray, tcfg: dict, quiet: bool = False) -> tuple[int, int] | None:
    """Top-left of the WP template (platform + right brazier). An NPC at the right brazier spoils
    the full match (0.66 live), so also accept the left half alone, or a weaker full match right
    where the route normally ends."""
    from .vision.screen import match_score

    t = bot._templates.get("town_wp_full")
    if t is None:
        t = bot._templates["town_wp_full"] = cv2.imread(str(ASSETS / tcfg["wp_template"]))
    score, loc = match_score(frame, t, None)
    if score >= tcfg.get("wp_threshold", 0.7):
        return loc
    half, hloc = match_score(frame, t[:, : t.shape[1] // 2], None)
    if half >= 0.8:  # live: 0.86-0.87 with someone on the right brazier
        return hloc
    typ = tcfg.get("wp_typical")
    if typ and score >= 0.6 and np.hypot(loc[0] - typ[0], loc[1] - typ[1]) < 40:
        return loc
    if not quiet:
        log.info("town WP not matched: full %.2f at %s, left half %.2f at %s", score, loc, half, hloc)
    return None


def open_town_wp(bot: Controller, tcfg: dict) -> None:
    closed = False
    for attempt in range(3):
        view = bot.capture.grab()
        loc = find_town_wp(bot, view, tcfg)
        if loc is None and not closed:
            # a panel left open hides it (2026-11-03: the stash still up after a stowaway that dropped keys).
            # Esc closes it; if nothing was open that opens the game menu instead: Esc again
            bot.save_failure(f"town_wp_hidden_{attempt}")
            closed = True
            bot.press("esc")
            bot.kill.sleep(0.5)
            if bot.observe() == "esc_menu":
                bot.press("esc")
                bot.kill.sleep(0.5)
            view = bot.capture.grab()
            loc = find_town_wp(bot, view, tcfg)
        if loc is None:
            bot.save_failure(f"town_wp_not_found_{attempt}")
            raise BotError("town waypoint not visible at end of route")
        ox, oy = tcfg["wp_click_offset"]
        bot.click(loc[0] + ox, loc[1] + oy)
        try:
            bot.wait_for("wp_menu", 5)
            typ = tcfg.get("wp_typical")
            log.info("town WP template at %s", loc)
            if not ROUTE_END.exists() and attempt == 0 and typ and np.hypot(loc[0] - typ[0], loc[1] - typ[1]) < 40:
                cv2.imwrite(str(ROUTE_END), view)  # only a typical end (the first one saved was 190 px off)
                log.info("saved the town route end view")
            return
        except BotError:
            log.info("waypoint menu didn't open (attempt %d)", attempt + 1)
    raise BotError("could not open the town waypoint")


def check_area(bot: Controller, template: str) -> bool:
    """True if the area name (shown top-right only while the automap is open) matches.

    Tab toggles the automap and we don't know its current state, so: check, toggle and
    check, toggle and check. On success the automap is open, so close it again.
    """
    for i in range(3):
        if i:
            bot.press("tab")
            bot.kill.sleep(0.4)
        if bot.find(template, region=(1100, 20, 180, 70), threshold=0.75) is not None:
            bot.press("tab")
            bot.kill.sleep(0.3)
            return True
    return False


def recover_corpse(bot: Controller) -> None:
    """After a death the corpse lies at the new-game spawn; clicking our own feet picks it up
    (harmless when there's no corpse)."""
    x, y = bot.cfg["town"]["corpse_click"]
    bot.click(x, y)
    bot.kill.sleep(0.8)
    bot.observe()


def _tooltip_points(bot: Controller, region, step: int = 30):
    """Yield hover points in `region` where a name tooltip pops up above the cursor."""
    import cv2

    rx, ry, rw, rh = region
    bot.input.move(1270, 590)
    bot.kill.sleep(0.15)
    base = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
    for y in range(ry, ry + rh, step):
        for x in range(rx, rx + rw, step):
            bot.input.move(x, y)
            bot.kill.sleep(0.07)
            g = cv2.cvtColor(bot.capture.grab(), cv2.COLOR_BGR2GRAY).astype(np.int16)
            y0, x0 = max(0, y - 140), max(0, x - 120)
            if (np.abs(g[y0:y, x0 : x + 120] - base[y0:y, x0 : x + 120]) > 60).mean() > 0.02:
                yield x, y


def _name_points(bot: Controller, region, step: int = 30):
    """Yield hover points in `region` where an NPC/object name tooltip box appears."""
    from .vision.tooltip import find_tooltip

    rx, ry, rw, rh = region
    for y in range(ry, ry + rh, step):
        for x in range(rx, rx + rw, step):
            bot.input.move(x, y)
            bot.kill.sleep(0.08)
            if find_tooltip(bot.capture.grab(), x, y) is not None:
                yield x, y


ORMUS_SPRITE_MIN = 0.65  # his sprite poses score 0.76-0.88 where he stands, ~0.5 elsewhere (31 town frames)


def _sprite_hits(frame, names: list[str], region, min_score: float, max_hits: int = 3) -> list[tuple[int, int]]:
    """Centres of the best matches of NPC sprite poses (bot/assets/templates/npc/), best first, de-duplicated."""
    import cv2

    from .vision.screen import ASSETS

    rx, ry, rw, rh = region
    roi = frame[ry : ry + rh, rx : rx + rw]
    hits = []
    for n in names:
        t = cv2.imread(str(ASSETS / "npc" / n))
        if t is None or t.shape[0] > roi.shape[0] or t.shape[1] > roi.shape[1]:
            continue
        r = cv2.matchTemplate(roi, t, cv2.TM_CCOEFF_NORMED)
        for _ in range(2):
            _, mx, _, loc = cv2.minMaxLoc(r)
            if mx < min_score:
                break
            hits.append((mx, rx + loc[0] + t.shape[1] // 2, ry + loc[1] + t.shape[0] // 2))
            cv2.rectangle(r, (loc[0] - 20, loc[1] - 20), (loc[0] + 20, loc[1] + 20), -1.0, -1)
    out: list[tuple[int, int]] = []
    for _, x, y in sorted(hits, reverse=True):
        if all(abs(x - a) + abs(y - b) > 30 for a, b in out):
            out.append((x, y))
    return out[:max_hits]


def _ormus_points(bot: Controller, region):
    """Where to click for Ormus: his sprite first (poses from Botty, Stephen 2026-11-02: "detect his sprite
    rather than scanning for his name"), then the hover scan of `region`."""
    import time as _t

    import cv2

    frame = bot.capture.grab()
    names = [f"ormus_{i}.png" for i in range(6)]
    hits = _sprite_hits(frame, names, (0, 0, 1280, 560), ORMUS_SPRITE_MIN)
    best = _sprite_hits(frame, names, (0, 0, 1280, 560), 0.0, max_hits=1)
    log.info("Ormus sprite: %s (best anywhere %s)", hits or "not on screen", best)
    # frames for tuning the threshold (the hover scan says afterwards whether he was there)
    cv2.imwrite(str(Path(bot.cfg["paths"]["raw_frames"]) / f"ormus_sprite_{_t.strftime('%m%d-%H%M%S')}.png"), frame)
    bot.ormus_frame = frame  # _keep_ormus crops him from it once his dialog proves where he was
    yield from hits
    yield from _tooltip_points(bot, region)


def _keep_ormus(bot: Controller, x: int, y: int) -> None:
    """His dialog opened after a click at (x, y): save his sprite from the frame taken before the hover scan,
    for templates matched to Stephen's graphics (Botty's poses score < 0.65 here, 2026-11-02)."""
    import time as _t

    import cv2

    f = getattr(bot, "ormus_frame", None)
    if f is None:
        return
    x0, y0 = max(0, x - 50), max(0, y - 90)
    out = Path(bot.cfg["paths"]["raw_frames"]) / "ormus_crops"
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"{_t.strftime('%m%d-%H%M%S')}_{x}_{y}.png"), f[y0 : y + 90, x0 : x + 50])


def heal_at_ormus(bot: Controller) -> bool:
    """Walk toward the plaza, find Ormus by hover, talk to him (heals), close the dialog.
    The character ends up somewhere near Ormus, so the caller should start a new game."""
    tcfg = bot.cfg["town"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]])
    for attempt, (x, y) in enumerate(_ormus_points(bot, tcfg["ormus_region"])):
        if attempt >= 4:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        if bot.find("npc_ormus.png", region=(0, 0, 1280, 500), threshold=0.8) is not None:
            _keep_ormus(bot, x, y)
            bot.press("esc")
            log.info("healed by Ormus")
            return True
        bot.press("esc")  # someone else's dialog (or nothing); keep looking
        bot.kill.sleep(0.3)
    bot.save_failure("ormus_not_found")
    return False


def belt_full(bot: Controller) -> bool:
    from .vision.orbs import belt_slots

    return all(belt_slots(bot.capture.grab(), bot.cfg["vision"]["belt"]))


def buy_mana_at_ormus(bot: Controller, max_clicks: int = 8) -> bool:
    """Meph runs only (Stephen 2026-10-30: potions may be bought for Meph; LK stays chest rejuvs only).
    Walk to Ormus, Trade (opens on Misc), shift+right-click his best mana potion (bottom of the right
    column) until the 4 visible belt slots hold a potion. Mana = Energy Shield: answers Wyand's Mana Burn.
    Leaves her near Ormus: the caller starts a new game. True if the belt reads full."""
    tcfg = bot.cfg["town"]
    o = tcfg["ormus"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]])
    for attempt, (x, y) in enumerate(_ormus_points(bot, tcfg["ormus_region"])):
        if attempt >= 5:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        loc = bot.find("npc_ormus.png", region=(0, 0, 1280, 500), threshold=0.8)
        if loc is None:
            bot.press("esc")
            bot.kill.sleep(0.3)
            continue
        _keep_ormus(bot, x, y)
        bot.click(loc[0] + o["trade_offset"][0], loc[1] + o["trade_offset"][1])
        bot.kill.sleep(1.5)
        if bot.find("trade_ormus_misc.png", region=(0, 0, 640, 140), threshold=0.8) is None:
            bot.save_failure("ormus_trade_not_opened")
            bot.press("esc")
            return False
        from .vision.orbs import belt_kinds

        def kinds():
            return belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"])

        def buy(pt, shift: bool = True):
            if shift:
                bot.input.key_down("shift")
                bot.kill.sleep(0.05)
            bot.click(*pt, "right")
            bot.kill.sleep(0.05)
            if shift:
                bot.input.key_up("shift")
            bot.kill.sleep(0.5)

        # Shift+right-click fills every empty belt column with that potion (live 2026-11-01: 4 x red).
        # So: one red (plain right-click) claims the first empty column, shift-blue fills the rest,
        # shift-red tops up the red column. Belt = 1 column red (life), 3 blue (mana = the shield).
        if not any(k in ("hp", "rejuv") for k in kinds()) and None in kinds():
            buy(o["healing_potion"], shift=False)
        for i in range(3):
            if None not in kinds():
                break
            buy(o["mana_potion"])
        # no "top-up" buy: with the column full it lands in the inventory and the stowaway stashed it (Stephen
        # 2026-11-02: healing + mana potions piling up on shared page 1)
        ok = None not in kinds()
        bot.press("esc")
        bot.kill.sleep(0.5)
        log.info("Ormus: potions bought, belt %s %s", kinds(), "full" if ok else "NOT full")
        if not ok:
            bot.save_failure("belt_not_full_after_buying")
        return ok
    bot.save_failure("ormus_not_found")
    return False


def chat(bot: Controller, text: str) -> bool:
    """Type a chat line / command (Enter, text, Enter). Types only once the chat input line shows:
    keys sent without it are hotkeys (2026-10-30 that flipped the automap fade and changed skills)."""
    from .gamesettings import chat_open

    names = {" ": "space", "/": "/"}
    for _ in range(2):
        if bot.observe() != "in_game":  # Enter on the Esc menu would press its highlighted button
            bot.press("esc")
            bot.kill.sleep(0.6)
            continue
        bot.press("enter")
        bot.kill.sleep(0.4)
        if chat_open(bot.capture.grab()):
            break
    else:
        bot.save_failure("chat_not_open")
        log.warning("chat didn't open; not typing %r", text)
        return False
    for ch in text:
        bot.press(names.get(ch, ch))
        bot.kill.sleep(0.04)
    bot.press("enter")
    bot.kill.sleep(0.3)
    return True


def set_players(bot: Controller, n: int) -> bool:
    """/players N: monster difficulty of an N-player game (chest loot unaffected, per Stephen).
    D2R keeps it as a setting ("Offline Difficulty Scaling"), so the caller skips it when that matches."""
    if not chat(bot, f"/players {n}"):
        return False
    bot.kill.sleep(0.3)
    import cv2

    cv2.imwrite(str(bot.cfg["paths"]["raw_frames"] / "players_set.png"), bot.capture.grab())  # evidence
    log.info("set /players %d", n)
    return True


def buy_keys(bot: Controller, h: dict) -> int | None:
    """Trade window open: Misc tab, buy keys until the inventory stack reads full (key_count 12).
    2026-10-27: one shift+right-click left the stack at 1 of 12 while the estimate said 12, so the
    bot stopped picking keys up. Returns the last count read (None: no stack found)."""
    from .vision.durability import key_count
    from .vision.inventory import cell_center

    bot.click(*h["misc_tab"])
    bot.kill.sleep(0.5)
    n = None
    for i in range(12):
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(*h["key"], "right")
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.kill.sleep(0.5)
        keys = _scan_inventory(bot)["key"]
        if not keys:
            continue
        bot.input.move(*cell_center(*keys[0]))
        bot.kill.sleep(0.35)
        n = key_count(bot.capture.grab())
        if i == 0:
            bot.save_failure("keys_after_first_buy")  # evidence while this is new
        if n == 12:
            break
    log.info("bought keys: stack reads %s", n)
    if n is not None:
        bot.keys_left = 6 if n == 3 else n  # 3 = "3 to 9"
    return n


def repair_at_hratli(bot: Controller, keys: bool = True) -> bool:
    """From spawn: walk past Ormus, SE over the bridge, NE at the landing to Hratli's forge
    (route from Stephen, recorded 2026-10-26), open Trade/Repair, Repair All. Like the Ormus detour,
    this leaves us far from the WP, so the caller should start a new game."""
    tcfg = bot.cfg["town"]
    h = tcfg["hratli"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]] + h["route"])
    # Shape-based tooltip finder: the forge fire flickers, which fooled the frame-diff one.
    for attempt, (x, y) in enumerate(_name_points(bot, h["region"])):
        if attempt >= 5:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        loc = bot.find("npc_hratli.png", region=(0, 0, 1280, 500), threshold=0.8)
        if loc is None:
            bot.press("esc")  # someone else's dialog (or nothing); keep looking
            bot.kill.sleep(0.3)
            continue
        bot.click(loc[0] + h["trade_offset"][0], loc[1] + h["trade_offset"][1])
        for _ in range(10):
            bot.kill.sleep(0.3)
            if bot.find("trade_repair_all.png", region=(300, 460, 120, 100), threshold=0.8) is not None:
                break
        else:
            bot.save_failure("hratli_trade_not_opened")
            bot.press("esc")
            return False
        bot.click(*h["repair_all"])
        bot.kill.sleep(1.0)
        if keys:
            buy_keys(bot, h)
        bot.press("esc")
        bot.kill.sleep(0.5)
        log.info("repaired at Hratli")
        return True
    bot.save_failure("hratli_not_found")
    log.warning("Hratli not found; no repair")
    return False


def merc_alive(bot: Controller, tries: int = 3) -> bool:
    """The merc portrait (top-left) shows only while the merc is alive. Retries a few times:
    it may not be drawn yet right after a game loads."""
    for i in range(tries):
        if i:
            bot.kill.sleep(0.5)
        if bot.find("merc_portrait.png", region=tuple(bot.cfg["town"]["merc_region"]),
                    threshold=0.85) is not None:
            return True
    return False


def revive_merc(bot: Controller) -> bool:
    """From spawn: walk past Ormus, NW along the boardwalk into Asheara's hut (route from Stephen,
    recorded 2026-10-26), Resurrect (50k gold). Leaves us far from the WP: caller starts a new game."""
    tcfg = bot.cfg["town"]
    a = tcfg["asheara"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]] + a["route"])
    for attempt, (x, y) in enumerate(_name_points(bot, a["region"])):
        if attempt >= 5:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        loc = bot.find("npc_asheara.png", region=(0, 0, 1280, 500), threshold=0.85)
        if loc is None:
            bot.press("esc")  # someone else's dialog (or nothing); keep looking
            bot.kill.sleep(0.3)
            continue
        bot.click(loc[0] + a["resurrect_offset"][0], loc[1] + a["resurrect_offset"][1])
        bot.kill.sleep(1.5)
        bot.press("esc")
        bot.kill.sleep(0.5)
        if merc_alive(bot):
            log.info("merc resurrected at Asheara")
            return True
        bot.save_failure("merc_not_resurrected")
        log.warning("merc still dead after Resurrect (not enough gold?): withdrawing at the next stash stop")
        from . import state

        state.save({**state.load(), "gold_needed": True})
        return False
    bot.observe()  # the failure frame should show where the search ended, not the game's first frame
    bot.save_failure("asheara_not_found")
    log.warning("Asheara not found; merc not revived")
    return False


def needs_heal(bot: Controller) -> bool:
    bot.observe()
    return bot.hp is not None and bot.hp < bot.cfg["town"]["heal_below_pct"]


def cast_buffs(bot: Controller) -> None:
    """Cast each buff (select it on right-click, right-click on ourselves), then put Teleport back."""
    hk = bot.cfg["hotkeys"]
    for name in hk.get("buffs", []):
        bot.press(hk["skills"][name])
        bot.kill.sleep(0.1)
        bot.click(*bot.cfg["town"]["corpse_click"], "right")
        bot.kill.sleep(0.3)  # casts take < 0.2 s (tools/tp_rate.py)
    bot.press(hk["skills"]["teleport"])
    bot.kill.sleep(0.15)


WARCRY_SWAP_S = 0.25  # the set changes this long after the key
WARCRY_CAST_S = 0.6   # no faster-cast gear on the swap set
WARCRY_PANEL_S = 0.35  # the inventory panel is up by then


def read_weapon_set(bot: Controller) -> int | None:
    """Active weapon set, read from the inventory panel's tabs (open for a moment). The swap key is a toggle: a
    lost press inverts every later swap, so she'd stay on the flail with no war cries (2026-11-03: max life 401
    in 7 of 8 chicken frames from 17:58 on)."""
    from .vision.inventory import weapon_set

    inv = bot.cfg["hotkeys"]["inventory"]
    bot.press(inv)
    try:
        bot.sleep(WARCRY_PANEL_S)
        return weapon_set(bot.capture.grab())
    finally:
        bot.press(inv)
        bot.sleep(0.1)


def _swap_to(bot: Controller, want: int, tries: int = 3) -> bool:
    """Press swap and read the set until it's `want`. False if it never is, or the tabs can't be read."""
    for _ in range(tries):
        bot.press(bot.cfg["hotkeys"]["swap_weapons"])
        bot.sleep(WARCRY_SWAP_S)
        now = read_weapon_set(bot)
        if now == want:
            return True
        if now is None:
            return False
    return False


def cast_warcries(bot: Controller) -> None:
    """Swap to Call to Arms and check it's up, cast `hotkeys.warcries`, swap back and check, select Teleport.
    Only outside town (the game refuses war cries there). Reads the set both ways because the swap key is a
    toggle: counting presses can't notice a lost one. An exception on the way (chicken, F12), or tabs that can't
    be read, leave `weapons_dirty` for the next game's check."""
    hk = bot.cfg["hotkeys"]
    if not hk.get("warcries"):
        return
    main = hk["main_weapon_set"]
    bot.weapons_dirty = True
    on_flail = _swap_to(bot, 3 - main)
    if on_flail:
        try:
            for name in hk["warcries"]:
                bot.press(hk["skills"][name])
                bot.sleep(0.1)
                bot.click(*bot.cfg["town"]["corpse_click"], "right", hover=0)
                bot.sleep(WARCRY_CAST_S)
        except BaseException:
            bot.press(hk["swap_weapons"])  # a chicken mid-cast: no time to read it, the next game checks
            raise
        back = _swap_to(bot, main)
    else:
        back = read_weapon_set(bot) == main or _swap_to(bot, main)
    bot.press(hk["skills"]["teleport"])
    bot.sleep(0.1)
    if not back:
        bot.save_failure("weapon_set_unknown")
        log.warning("war cries: couldn't confirm the main weapon set")
        return
    bot.weapons_dirty = False
    if on_flail:
        bot.warcries_at = bot.clock()
        log.info("war cries cast: HP %s MP %s", bot.hp, bot.mp)
    else:
        log.warning("war cries not cast: Call to Arms never came up")


def refresh_warcries(bot: Controller) -> bool:
    """Cast again once `hotkeys.warcry_refresh_s` have passed since the last cast. True if it cast."""
    age = bot.cfg["hotkeys"].get("warcry_refresh_s")
    if not age or bot.clock() - getattr(bot, "warcries_at", 0) < age:
        return False
    cast_warcries(bot)
    return True


def ensure_main_weapons(bot: Controller) -> None:
    """At a game's start: back to the main set if a session began swapped (Stephen's own play) or a run ended
    during the war cries. Checked once a session and after such a run; costs one look at the inventory."""
    from .vision.inventory import weapon_set

    if not getattr(bot, "weapons_dirty", True):
        return
    hk = bot.cfg["hotkeys"]
    bot.press(hk["inventory"])
    bot.kill.sleep(0.5)
    bot.input.move(640, 600)
    bot.kill.sleep(0.15)
    now = weapon_set(bot.capture.grab())
    if now is not None and now != hk["main_weapon_set"]:
        log.info("weapon set %d is up: swapping back to %d", now, hk["main_weapon_set"])
        bot.press(hk["swap_weapons"])
        bot.kill.sleep(0.5)
        now = weapon_set(bot.capture.grab())
    bot.press(hk["inventory"])
    bot.kill.sleep(0.3)
    if now != hk["main_weapon_set"]:
        bot.save_failure("weapon_set_unknown")
        log.warning("weapon set reads %s, wanted %s", now, hk["main_weapon_set"])
        return
    bot.weapons_dirty = False


def open_stash(bot: Controller, attempts: int = 3) -> bool:
    """Click the stash chest (found by template; the route's end point varies by a few dozen px)
    and wait for its panel. An NPC (often Cain) standing on it eats the click and opens a dialog:
    close it with Esc and try again."""
    scfg = bot.cfg["stash"]
    for attempt in range(attempts):
        loc = bot.find("town_stash.png", region=(0, 0, 1280, 560), threshold=0.75)
        if loc is not None:
            x, y = loc[0] + 25, loc[1] + 28  # template is 50x48; click the chest's lower middle
        else:
            log.info("stash template not found; clicking the configured spot")
            x, y = scfg["click"]
        bot.click(x, y)
        for _ in range(12):
            bot.kill.sleep(0.3)
            if bot.find("stash_open.png", region=(165, 16, 110, 42), threshold=0.8) is not None:
                return True
        log.info("stash didn't open (attempt %d)", attempt + 1)
        bot.press("esc")  # close an NPC dialog if we clicked one
        bot.kill.sleep(1.0)
    bot.save_failure("stash_not_opened")
    log.warning("stash didn't open; skipping restock")
    return False


def withdraw_gold(bot: Controller) -> bool:
    """After a revive failed for gold (logs/state.json gold_needed): take `stash.withdraw_gold` from the shared
    stash's gold (Stephen keeps it there, 2026-11-01). True if done."""
    from . import state

    if not state.load().get("gold_needed") or not open_stash(bot):
        return False
    scfg = bot.cfg["stash"]
    bot.click(*scfg["shared_tab"])
    bot.kill.sleep(0.4)
    bot.click(*scfg["gold_button"])
    bot.kill.sleep(0.8)
    for _ in range(8):  # the box opens with the most she can carry; clear it
        bot.press("backspace")
        bot.kill.sleep(0.05)
    for ch in str(scfg["withdraw_gold"]):
        bot.press(ch)
        bot.kill.sleep(0.05)
    bot.kill.sleep(0.3)
    bot.click(*scfg["withdraw_ok"])
    bot.kill.sleep(0.6)
    bot.press("esc")
    bot.kill.sleep(0.4)
    state.save({**state.load(), "gold_needed": False})
    log.info("withdrew %d gold from the shared stash", scfg["withdraw_gold"])
    return True


def belt_needs_restock(bot: Controller) -> bool:
    """An empty belt slot and rejuvs left in the stash (what restock_belt would act on)."""
    from .vision.orbs import belt_slots

    from . import state

    bot.observe()
    return not all(belt_slots(bot.frame, bot.cfg["vision"]["belt"])) and not state.load().get("stash_rejuvs_empty")


def _stash_cell(frame: np.ndarray, pt) -> np.ndarray:
    x, y = pt
    return frame[y - 18:y + 18, x - 18:x + 18].copy()


def _has_potion(cell: np.ndarray) -> bool:
    """A rejuv stack's purple (empty stash cells are dark gray)."""
    hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)
    return float(((hsv[..., 1] > 80) & (hsv[..., 2] > 60)).mean()) > 0.05


def restock_belt(bot: Controller) -> int:
    """If any visible belt slot is empty, open the stash (next to the town WP) and shift-click
    Full Rejuvenation Potions from the Materials tab until the belt row is full. Returns potions moved."""
    from .vision.orbs import belt_slots

    from . import state

    scfg = bot.cfg["stash"]
    belt = bot.cfg["vision"]["belt"]
    bot.observe()
    if all(belt_slots(bot.frame, belt)):
        return 0
    if state.load().get("stash_rejuvs_empty"):  # 4 s a run for nothing (bot/supplies.py)
        return 0
    if not open_stash(bot):
        return 0
    bot.click(*scfg["materials_tab"])
    bot.kill.sleep(0.5)
    # Watch the stash stack, not the belt: shift-click fills hidden rows of columns that already hold potions,
    # so the visible row often doesn't change (2026-11-02: read as "stash slot empty" -> 0-1 potions a restock,
    # empty belts in Meph fights). A click that changes the stack's picture (its count) moved a potion; one that
    # doesn't means the belt is full, or that stack is gone (no purple left) -> the next stack (Rejuvs).
    moved = 0
    slots = list(scfg["rejuv_slots"])
    for _ in range(scfg.get("max_potions", 16) + len(slots)):
        if not slots:
            break
        bot.input.move(1270, 590)
        bot.kill.sleep(0.15)
        before = _stash_cell(bot.capture.grab(), slots[0])
        if not _has_potion(before):
            slots.pop(0)
            continue
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(*slots[0])
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.input.move(1270, 590)
        bot.kill.sleep(0.35)
        after = _stash_cell(bot.capture.grab(), slots[0])
        if int((np.abs(after.astype(np.int16) - before.astype(np.int16)).max(axis=2) > 40).sum()) < 8:
            break  # nothing moved: the belt is full
        moved += 1
    dry = supplies.restocked(moved, slots_gone=not slots)
    if dry:  # the Materials tab as she saw it: why zero potions moved
        bot.observe()
        bot.save_failure("restock_dry")
        log.warning("stash is out of rejuvs; no more restocks until some are stashed or the next session")
    bot.press("esc")
    bot.kill.sleep(0.5)
    log.info("restocked belt with %d potions", moved)
    return moved


def _ctrl_click(bot: Controller, x: int, y: int) -> None:
    bot.input.key_down("ctrl")
    bot.kill.sleep(0.05)
    bot.click(x, y)
    bot.kill.sleep(0.05)
    bot.input.key_up("ctrl")
    bot.kill.sleep(0.3)


def _scan_inventory(bot: Controller) -> dict:
    from .vision.inventory import protected_cells, scan

    bot.input.move(640, 600)  # no tooltip over the grid
    bot.kill.sleep(0.15)
    tpl = bot._templates.get("inv_key.png")
    if tpl is None:
        tpl = bot._templates["inv_key.png"] = cv2.imread(str(ASSETS / "inv_key.png"))
    return scan(bot.capture.grab(), tpl, protected_cells(bot.cfg["inventory"]["protected"]))


LOOT_CSV = ROOT / "logs" / "loot.csv"
REJUV_SCORE = 0.8  # label_rejuv.png ("Rejuvenation") in stash tooltips: 1.00 on rejuvs, <= 0.45 on runes/charms


def _is_charm(frame: np.ndarray, x: int, y: int) -> bool:
    """The tooltip says "... Charm" (name or base type line: Gheed's Fortune goes with the charms too)."""
    from .vision.labels import has_word

    crop = frame[max(0, y - 420) : y, max(0, x - 300) : x + 300]
    return has_word(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), "word_charm.png")


def _is_stack_item(frame: np.ndarray, x: int, y: int) -> bool:
    """The tooltip says "Ctrl + Left Click to Move to Stack Tab": gems, skulls, runes, essences. A full stack leaves
    it in the inventory, which says nothing about room on the stash pages. 2091 saved tooltips: 1.00 or <= 0.62."""
    from .vision.labels import has_word

    crop = frame[max(0, y - 420) : y, max(0, x - 300) : x + 300]
    return has_word(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), "word_stack_tab.png")


def _is_orange(bot: Controller, frame: np.ndarray, x: int, y: int) -> bool:
    """Orange name: a rune or an essence."""
    from .vision.tooltip import name_kind

    colored = {k: v for k, v in bot.cfg["vision"]["labels"].items() if k != "white"}
    return name_kind(frame, x, y, colored) == "rune"


def _is_rejuv(bot: Controller, frame: np.ndarray, x: int, y: int) -> bool:
    tpl = bot._templates.get("label_rejuv.png")
    if tpl is None:
        tpl = bot._templates["label_rejuv.png"] = cv2.imread(str(ASSETS / "label_rejuv.png"))
    crop = frame[max(0, y - 420) : y, max(0, x - 300) : x + 300]
    return float(cv2.matchTemplate(crop, tpl, cv2.TM_CCOEFF_NORMED).max()) >= REJUV_SCORE


def _log_loot(items: list[str]) -> None:
    """Append stashed items to logs/loot.csv (time, item) so Stephen can see what the bot found."""
    import time

    if not items:
        return
    LOOT_CSV.parent.mkdir(exist_ok=True)
    with open(LOOT_CSV, "a") as f:
        for it in items:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{it}\n")
    log.info("stashed: %s", ", ".join(items))


def _save_tooltip(bot: Controller, x: int, y: int) -> np.ndarray:
    """Hover an inventory item and keep its tooltip (logs/loot/<time>.png): names unique rings.
    Returns the frame."""
    import time

    bot.input.move(x, y)
    bot.kill.sleep(0.35)
    out = LOOT_CSV.parent / "loot"
    out.mkdir(parents=True, exist_ok=True)
    frame = bot.capture.grab()
    cv2.imwrite(str(out / f"{time.strftime('%Y%m%d-%H%M%S')}_{x}_{y}.png"), frame[:, 400:1280])
    return frame


def count_keys(bot: Controller) -> int | None:
    """Keys in the inventory, as a lower bound (vision/durability.key_count: 12, 11, 10, 3 = "3-9",
    2, 1 per stack, summed). None if there's no key stack. The estimate in logs/state.json drifts
    (one pickup can be several keys), so check before buying."""
    from .vision.durability import key_count
    from .vision.inventory import cell_center

    bot.press(bot.cfg["hotkeys"]["inventory"])
    bot.kill.sleep(0.35)
    try:
        keys = _scan_inventory(bot)["key"]
        total = None
        for cell in keys:
            bot.input.move(*cell_center(*cell))
            bot.kill.sleep(0.35)
            n = key_count(bot.capture.grab())
            total = (total or 0) + (n or 0)
        return total
    finally:
        bot.input.move(640, 600)
        bot.press(bot.cfg["hotkeys"]["inventory"])
        bot.kill.sleep(0.2)


def durability_ok(bot: Controller) -> bool:
    """Hover each equipped item (inventory open) and compare "Durability: X of Y" (vision/durability.py).
    False if any item is below full. Items without a durability line (or no tooltip) don't count."""
    from .vision.durability import durability_full

    bot.press(bot.cfg["hotkeys"]["inventory"])
    bot.kill.sleep(0.35)
    worn = []
    try:
        for name, (x, y) in bot.cfg["inventory"]["equipment"].items():
            bot.input.move(x, y)
            bot.kill.sleep(0.35)
            if durability_full(bot.capture.grab()) is False:
                worn.append(name)
    finally:
        bot.input.move(640, 600)
        bot.press(bot.cfg["hotkeys"]["inventory"])
        bot.kill.sleep(0.2)
    if worn:
        log.info("durability below full: %s", ", ".join(worn))
    return not worn


def _spill_to_shared_pages(bot: Controller, spill: list, left: list) -> list:
    """Shared page 1 and the personal tab are full: try pages 5, 4, 3, 2 (Stephen sorts those, so last; at ~40 items
    an hour a full stash would otherwise strand Mephisto's drops), then back to page 1. Returns what's still left."""
    scfg = bot.cfg["stash"]
    bot.click(*scfg["shared_tab"])
    bot.kill.sleep(0.4)
    for _ in range(4):
        bot.click(*scfg["shared_next_page"])
        bot.kill.sleep(0.15)
    for page in range(5, 1, -1):
        log.info("stowaway: %d item(s) to try on shared page %d", len(spill), page)
        for cell in spill:
            _ctrl_click(bot, *cell_center_of(cell))
        left = _scan_inventory(bot)["other"]
        spill = [cell for cell in spill if cell in left]
        if not spill:
            break
        bot.click(*scfg["shared_prev_page"])
        bot.kill.sleep(0.3)
    for _ in range(4):
        bot.click(*scfg["shared_prev_page"])
        bot.kill.sleep(0.15)
    return left


def cell_center_of(cell: tuple[int, int]) -> tuple[int, int]:
    from .vision.inventory import cell_center

    return cell_center(*cell)


def stowaway(bot: Controller, stash: bool = True) -> dict | None:
    """At the stash stop: Ctrl+click loot (runes, unique rings: anything outside Stephen's protected
    cells that isn't a key) into the stash, then drop key stacks beyond one (pickups add whole stacks;
    2026-10-26 eight full stacks had filled the inventory). Runes auto-route to the Runes tab; the rest
    goes to shared page 1. An extra key stack means the kept one is full, so keys_left becomes 12.
    `stash=False` (no stash nearby, e.g. the A4 spawn): keys only; None if there's loot for the stash."""
    from . import state
    from .vision.inventory import cell_center, is_empty, runes_added

    bot.press(bot.cfg["hotkeys"]["inventory"])
    bot.kill.sleep(0.35)
    inv = _scan_inventory(bot)
    bot.press(bot.cfg["hotkeys"]["inventory"])
    bot.kill.sleep(0.2)
    if inv["other"] and not stash:
        return None
    done = {"stashed": 0, "dropped": 0}
    if inv["other"]:
        if open_stash(bot):
            scfg = bot.cfg["stash"]
            bot.click(*scfg["runes_tab"])  # before/after shots of the Runes tab name the runes
            bot.input.move(640, 600)
            bot.kill.sleep(0.4)
            runes_before = bot.capture.grab()
            tab = None
            items = charms = 0
            rejuv_cells = set()
            stack_cells, keep_cells = set(), set()
            for i, (c, r) in enumerate(inv["other"]):
                if i:  # a grand/large charm fills 2-3 cells: its other cells are empty once it's stashed
                    bot.input.move(640, 600)
                    bot.kill.sleep(0.15)
                    if is_empty(bot.capture.grab(), c, r):
                        continue
                tip = _save_tooltip(bot, *cell_center(c, r))
                charm = _is_charm(tip, *cell_center(c, r))
                if _is_rejuv(bot, tip, *cell_center(c, r)):
                    rejuv_cells.add((c, r))
                elif _is_stack_item(tip, *cell_center(c, r)):
                    stack_cells.add((c, r))
                    if _is_orange(bot, tip, *cell_center(c, r)):
                        keep_cells.add((c, r))
                want = "personal_tab" if charm else "shared_tab"
                if tab != want:
                    bot.click(*scfg[want])
                    bot.kill.sleep(0.4)
                    tab = want
                _ctrl_click(bot, *cell_center(c, r))
                items += 1
                charms += charm
            left = _scan_inventory(bot)["other"]
            retry = [cell for cell in left if cell in stack_cells]
            if retry:  # one more try, so that a missed click isn't taken for a full stack
                for cell in retry:
                    _ctrl_click(bot, *cell_center(*cell))
                left = _scan_inventory(bot)["other"]
            spill = supplies.needs_a_page(left, rejuv_cells, stack_cells)
            if spill:  # that tab is full: try the other one (Stephen clears both between sessions, 2026-10-31)
                other = "shared_tab" if tab == "personal_tab" else "personal_tab"
                log.info("stowaway: %d item(s) didn't fit; trying the %s", len(spill), other.replace("_", " "))
                bot.click(*scfg[other])
                bot.kill.sleep(0.4)
                for cell in spill:
                    _ctrl_click(bot, *cell_center(*cell))
                left = _scan_inventory(bot)["other"]
                spill = supplies.needs_a_page(left, rejuv_cells, stack_cells)
                if spill and not getattr(bot, "stash_full", False):  # once full it stays full: no tour every game
                    left = _spill_to_shared_pages(bot, spill, left)
                    bot.stash_full = bool(supplies.needs_a_page(left, rejuv_cells, stack_cells))
            done["stashed"] = max(0, items - len(left))
            bot.click(*scfg["runes_tab"])
            bot.input.move(640, 600)
            bot.kill.sleep(0.4)
            runes = runes_added(runes_before, bot.capture.grab())
            stuck = [cell for cell in left if cell in rejuv_cells]  # their Materials stack is at 99
            rejuvs = len(rejuv_cells) - len(stuck)
            others = done["stashed"] - len(runes) - charms - rejuvs
            full_stacks = [cell for cell in left if cell in stack_cells and cell not in keep_cells]
            _log_loot([f"{n} Rune" for n in runes] + ["Charm to personal tab"] * charms
                      + ["Rejuvenation Potion to Materials tab"] * rejuvs + ["item to shared tab"] * max(0, others)
                      + ["dropped: its stash stack is full"] * len(full_stacks))
            done["runes"] = runes
            left = [cell for cell in left if cell not in rejuv_cells and cell not in full_stacks]
            if left:
                if not getattr(bot, "stash_full", False):
                    bot.save_failure("stowaway_left_items")
                log.warning("stowaway: %d item(s) stayed in the inventory (stash page full?): %s", len(left), left)
            bot.press("esc")
            bot.kill.sleep(0.4)
            if rejuv_cells:
                # a stash stack holds 99 (Stephen 2026-10-31): once full, stop picking spares until a restock
                # takes some out, and drop the ones that didn't fit
                st = {**state.load(), "rejuv_stash_full": bool(stuck)}
                state.save(supplies.after_stowing(st, rejuvs, bool(stuck)))
            if stuck:
                log.info("stowaway: rejuv stack full (99); dropping %d spare rejuv(s), no spares until a restock",
                         len(stuck))
                bot.press(bot.cfg["hotkeys"]["inventory"])
                bot.kill.sleep(0.35)
                for cell in stuck:
                    _ctrl_click(bot, *cell_center(*cell))  # Ctrl+click with only the inventory open = drop
                bot.press(bot.cfg["hotkeys"]["inventory"])
                bot.kill.sleep(0.2)
            if full_stacks:
                if not getattr(bot, "full_stack_seen", False):  # one frame a session: shows what the game did
                    bot.full_stack_seen = True
                    bot.save_failure("stack_full_dropping")
                log.warning("stowaway: stack full, dropping %d item(s); tooltips in logs/loot", len(full_stacks))
                bot.press(bot.cfg["hotkeys"]["inventory"])
                bot.kill.sleep(0.35)
                for cell in full_stacks:
                    _ctrl_click(bot, *cell_center(*cell))  # Ctrl+click with only the inventory open = drop
                bot.press(bot.cfg["hotkeys"]["inventory"])
                bot.kill.sleep(0.2)
    keys = inv["key"]
    st = state.load()
    if len(keys) > 1:
        kept = tuple(st.get("key_cell") or ())
        kept = kept if kept in keys else keys[0]
        bot.press(bot.cfg["hotkeys"]["inventory"])
        bot.kill.sleep(0.35)
        for cell in keys:
            if cell != kept:
                _ctrl_click(bot, *cell_center(*cell))  # Ctrl+click with only the inventory open = drop
                done["dropped"] += 1
        still = _scan_inventory(bot)["key"]
        bot.press(bot.cfg["hotkeys"]["inventory"])
        bot.kill.sleep(0.2)
        if len(still) > 1:
            log.warning("stowaway: %d key stacks still in the inventory", len(still))
        bot.keys_left = bot.cfg["town"]["keys_full"]
        st = {**st, "key_cell": list(kept), "keys_left": bot.keys_left}
    elif len(keys) == 1:
        st = {**st, "key_cell": list(keys[0])}
    else:
        bot.keys_left = 0
        st = {**st, "key_cell": None, "keys_left": 0}
    state.save(st)
    log.info("stowaway: stashed %d, dropped %d key stack(s), %d free cells", done["stashed"], done["dropped"],
             len(inv["empty"]) + done["stashed"] + done["dropped"])
    return done


ARRIVAL_CHANGED = 0.05  # share of changed pixels: town -> LK measured 0.20, same spot with NPCs moving 0.002


def arrived(town_view: np.ndarray, frame: np.ndarray) -> bool:
    """The view's right half (the waypoint panel covers the left) no longer shows the town."""
    a, b = town_view[:560, 700:], frame[:560, 700:]
    return float((np.abs(a.astype(np.int16) - b).max(axis=2) > 40).mean()) > ARRIVAL_CHANGED


def wait_arrival(bot: Controller, town_view: np.ndarray, timeout: float = 30) -> None:
    """After picking a waypoint the town frame lingers a moment, then a loading screen shows,
    often too briefly to catch. Done once we're in game after a loading screen, or the view changed."""
    deadline = bot.clock() + timeout
    loaded = False
    while True:
        s = bot.observe()
        loaded = loaded or s == "loading"
        if s == "in_game" and (loaded or arrived(town_view, bot.frame)):
            return
        if bot.clock() >= deadline:
            bot.save_failure(f"no_arrival_{s}")
            raise BotError(f"waypoint travel: no arrival after {timeout}s; last state {s!r}")
        bot.kill.sleep(0.05)


def town_to_lower_kurast(bot: Controller, arrived_check=None, stow: bool = False) -> None:
    town_to_wp(bot, "wp_lower_kurast", "area_lower_kurast.png", arrived_check, stow)


def town_to_wp(bot: Controller, dest: str, area: str | None, arrived_check=None, stow: bool = False) -> None:
    """A3 spawn -> waypoint -> `dest` (a ui point on the Act III tab). `arrived_check`: optional quick
    test that we're there (e.g. the LK route's map fingerprint); when it passes, the slower automap
    area-name check (`area` template; None = skip) is skipped."""
    tcfg = bot.cfg["town"]
    bot.wait_for("in_game", 10)
    cast_buffs(bot)
    gave_up = walk_chain(bot, tcfg["route"], tcfg["route_disp"]) if tcfg.get("route_disp") else 0
    if gave_up is not None:  # roughly where that leg would have ended; fix_route_end corrects the rest
        walk_route(bot, tcfg["route"][gave_up:] if tcfg.get("route_disp") else tcfg["route"])
    restock_belt(bot)
    if withdraw_gold(bot):
        bot.merc_wait, bot.merc_fails = 0, 0  # revive on the next run
    if stow:
        stowaway(bot)
    fix_route_end(bot)  # after the restock: opening the stash walks us ~(160, 110) px to it
    open_town_wp(bot, tcfg)
    town_view = bot.capture.grab()
    bot.click_ui(dest)
    wait_arrival(bot, town_view)
    bot.guard(True)  # out of town from here on
    bot.wait_still(timeout=5)
    if not (arrived_check and arrived_check()) and area and not check_area(bot, area):
        bot.save_failure(f"not_at_{dest}")
        raise BotError(f"waypoint {dest}: arrived somewhere else")
    log.info("arrived at %s (HP %.0f%% MP %.0f%%)", dest, bot.hp or 0, bot.mp or 0)


# --- Act 4 starts --------------------------------------------------------------------------------
# A new game starts in the town of the act the character was saved in. Clean LK runs end with the
# LK waypoint -> Pandemonium Fortress, so the next game spawns 1.6 s from a waypoint instead of the
# ~12 s Kurast Docks walk (live 2026-10-27). Town upkeep (stash, Ormus, Hratli, Asheara) stays in
# Act 3: an Act 4 spawn that needs it takes the waypoint to Kurast Docks and starts a fresh game.

def spawn_act(bot: Controller) -> int:
    """4 if the Pandemonium Fortress waypoint is in view (it is from the A4 spawn), 1 if the Rogue
    Encampment spawn view is (Stephen played and ended in Act 1, 2026-10-31), else 3."""
    if find_a4_wp(bot):
        return 4
    if bot.find("a1_spawn.png", (120, 0, 560, 300), 0.75):
        return 1
    if bot.find("a2_spawn.png", (0, 0, 1280, 450), 0.75):  # Warriv's caravan, Lut Gholein (spawns vary a bit)
        return 2
    if bot.find("a5_spawn.png", (0, 0, 1280, 450), 0.85):  # Harrogath (other towns reach 0.73)
        return 5
    return 3


A1_WALK = (1150, 560)  # one click from the A1 spawn brings the waypoint into view (fixed map, live 2026-10-31)


def leave_act1(bot: Controller) -> None:
    """A1 spawn -> waypoint to Kurast Docks -> save & exit -> new game (spawns in Act 3)."""
    from .lifecycle import create_game, save_and_exit

    log.info("spawned in Act 1: waypoint to Act 3")
    bot.click(*A1_WALK)
    bot.kill.sleep(2.5)
    loc = bot.find("a1_wp.png", (0, 0, 1280, 600), 0.6)
    if loc is None:
        bot.save_failure("a1_wp_not_found")
        raise BotError("Act 1 waypoint not visible")
    bot.click(loc[0] + 62, loc[1] + 32)
    bot.wait_for("wp_menu", 5)
    wp_travel(bot, "wp_tab_act3", "wp_town")
    save_and_exit(bot)
    create_game(bot, bot.cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)


# Lut Gholein spawn -> waypoint: walk clicks found by tools/town_probe.py (2026-11-02): north through the palm
# square, north-east to the bazaar, north to Atma's tavern / the stash, then west and south-west. The town is
# fixed; the waypoint (a2_wp.png) shows at ~(175, 410) at the end. Checked after every click: stop when seen.
A2_WALK = [(640, 60), (640, 60), (640, 60), (1100, 200), (1100, 200), (1100, 150), (1100, 150), (1100, 150),
           (640, 60), (640, 60), (900, 60), (900, 60), (200, 330), (200, 330), (200, 500), (200, 500),
           # spawns vary, so the walk drifts: keep looking around the spot (it's west / south-west of the stash)
           (200, 400), (200, 400), (400, 560), (200, 550), (100, 330), (640, 560)]  # y <= 560: the HUD starts at 595
A2_WP_CLICK = (75, 45)  # from the template's top-left to the waypoint's centre


# Harrogath spawn -> waypoint: two clicks down-left (found 2026-11-02); a5_wp.png at ~(400, 490), just above the HUD
A5_WALK = [(250, 540), (250, 540), (250, 540), (400, 540), (150, 450)]
A5_WP_CLICK = (100, 62)


def _town_wp_by_walk(bot: Controller, act: int, walk, template: str, click_off) -> None:
    """Walk `walk` (clicks), looking for `template` after each; click it; waypoint to Kurast Docks ->
    save & exit -> new game (Act 3)."""
    from .lifecycle import create_game, save_and_exit

    log.info("spawned in Act %d: walking to its waypoint", act)
    vroot = ROOT / "maps" / "towns" / f"a{act}"
    if (vroot / "index.json").exists():
        # the town's view map (tools/town_map.py): find where we are, steer to the waypoint from any spawn
        from .townnav import walk_to_target
        from .vision.viewmap import ViewMap

        def seen():
            loc = bot.find(template, (0, 0, 1280, 600), 0.75)
            return (loc[0] + click_off[0], loc[1] + click_off[1]) if loc else None

        walk_to_target(bot, ViewMap.load(vroot), "wp", walk=walk, seen=seen)
        _wp_to_act3(bot)
        return
    loc = None
    for x, y in walk:
        bot.click(x, y)
        bot.kill.sleep(2.5)
        loc = bot.find(template, (0, 0, 1280, 600), 0.7)
        if loc is not None:
            break
    if loc is None:
        bot.save_failure(f"a{act}_wp_not_found")
        raise BotError(f"Act {act} waypoint not found along the walk")
    for attempt in range(3):
        bot.click(loc[0] + click_off[0], loc[1] + click_off[1])
        try:
            bot.wait_for("wp_menu", 5)
            break
        except BotError:
            loc = bot.find(template, (0, 0, 1280, 600), 0.6) or loc
    else:
        raise BotError(f"Act {act} waypoint menu didn't open")
    _wp_to_act3(bot)


def _wp_to_act3(bot: Controller) -> None:
    """Waypoint panel open in another act's town: Kurast Docks, save & exit, new game (it spawns in Act 3)."""
    from .lifecycle import create_game, save_and_exit

    wp_travel(bot, "wp_tab_act3", "wp_town")
    save_and_exit(bot)
    create_game(bot, bot.cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)


def leave_act2(bot: Controller) -> None:
    _town_wp_by_walk(bot, 2, A2_WALK, "a2_wp.png", A2_WP_CLICK)


def leave_act5(bot: Controller) -> None:
    _town_wp_by_walk(bot, 5, A5_WALK, "a5_wp.png", A5_WP_CLICK)


def leave_other_act(bot: Controller, act: int) -> bool:
    """Spawned in Act 1, 2 or 5 (Stephen's own game ended there): to Act 3. True if it did."""
    if act == 1:
        leave_act1(bot)
    elif act == 2:
        leave_act2(bot)
    elif act == 5:
        leave_act5(bot)
    else:
        return False
    return True


def find_a4_wp(bot: Controller) -> tuple[int, int] | None:
    tcfg = bot.cfg["town"]
    return bot.find(tcfg["a4_wp_template"], tcfg["a4_wp_region"], 0.7)


def open_a4_wp(bot: Controller) -> None:
    tcfg = bot.cfg["town"]
    for attempt in range(3):
        loc = find_a4_wp(bot)
        if loc is None:
            bot.save_failure(f"a4_wp_not_found_{attempt}")
            raise BotError("Act 4 waypoint not visible from the spawn")
        ox, oy = tcfg["a4_wp_click_offset"]
        bot.click(loc[0] + ox, loc[1] + oy)
        try:
            bot.wait_for("wp_menu", 5)
            return
        except BotError:
            log.info("A4 waypoint menu didn't open (attempt %d)", attempt + 1)
    raise BotError("could not open the Act 4 waypoint")


def wp_travel(bot: Controller, tab: str, dest: str) -> None:
    """With the waypoint panel open: pick the act tab, then the destination; wait until we're there."""
    bot.click_ui(tab)
    bot.kill.sleep(0.25)
    view = bot.capture.grab()
    bot.click_ui(dest)
    wait_arrival(bot, view)


def act4_to(bot: Controller, dest: str, arrived_check=None, area: str | None = "area_lower_kurast.png") -> None:
    """From the A4 spawn: buffs, waypoint -> `dest` on the Act III tab (out of town)."""
    bot.wait_for("in_game", 10)
    cast_buffs(bot)
    open_a4_wp(bot)
    wp_travel(bot, "wp_tab_act3", dest)
    bot.guard(True)
    bot.wait_still(timeout=5)
    if not (arrived_check and arrived_check()) and area and not check_area(bot, area):
        bot.save_failure(f"not_at_{dest}")
        raise BotError(f"waypoint {dest}: arrived somewhere else")
    log.info("arrived at %s from Act 4 (HP %.0f%% MP %.0f%%)", dest, bot.hp or 0, bot.mp or 0)


def restart_in_act3(bot: Controller) -> None:
    """A4 spawn -> waypoint to Kurast Docks -> save & exit -> new game (spawns in Act 3)."""
    from .lifecycle import create_game, save_and_exit

    log.info("town upkeep due: back to Act 3")
    open_a4_wp(bot)
    wp_travel(bot, "wp_tab_act3", "wp_town")
    save_and_exit(bot)
    create_game(bot, bot.cfg["game"]["difficulty"])
    bot.wait_for("in_game", 10)
