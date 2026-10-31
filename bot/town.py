"""M3: Act 3 town (Kurast Docks) -> waypoint -> Lower Kurast.

New games always start at the same spot by Meshif's boat, and the town layout is fixed,
so we walk a recorded route (config town.route) and then locate the waypoint by template.
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

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
    for attempt in range(3):
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


def heal_at_ormus(bot: Controller) -> bool:
    """Walk toward the plaza, find Ormus by hover, talk to him (heals), close the dialog.
    The character ends up somewhere near Ormus, so the caller should start a new game."""
    tcfg = bot.cfg["town"]
    walk_route(bot, tcfg["route"][: tcfg["ormus_after_leg"]])
    for attempt, (x, y) in enumerate(_tooltip_points(bot, tcfg["ormus_region"])):
        if attempt >= 4:
            break
        bot.click(x, y)
        bot.kill.sleep(2.0)
        if bot.find("npc_ormus.png", region=(0, 0, 1280, 500), threshold=0.8) is not None:
            bot.press("esc")
            log.info("healed by Ormus")
            return True
        bot.press("esc")  # someone else's dialog (or nothing); keep looking
        bot.kill.sleep(0.3)
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
        log.warning("merc still dead after Resurrect (not enough gold?)")
        return False
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


def belt_needs_restock(bot: Controller) -> bool:
    """An empty belt slot and rejuvs left in the stash (what restock_belt would act on)."""
    from .vision.orbs import belt_slots

    from . import state

    bot.observe()
    return not all(belt_slots(bot.frame, bot.cfg["vision"]["belt"])) and not state.load().get("stash_rejuvs_empty")


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
    if state.load().get("stash_rejuvs_empty"):  # 4 s a run for nothing; delete the flag from
        return 0                                 # logs/state.json after putting rejuvs in the stash
    if not open_stash(bot):
        return 0
    bot.click(*scfg["materials_tab"])
    bot.kill.sleep(0.5)
    moved = 0
    slots = list(scfg["rejuv_slots"])
    prev = None
    for _ in range(scfg.get("max_potions", 16)):
        bot.input.move(1270, 590)
        bot.kill.sleep(0.15)
        now = belt_slots(bot.capture.grab(), belt)
        if all(now):
            break
        if now == prev:  # last click moved nothing: that stash slot is empty, try the next
            slots.pop(0)
            moved -= 1
            if not slots:
                break
        prev = now
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(*slots[0])
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.kill.sleep(0.3)
        moved += 1
    else:
        bot.observe()
        bot.save_failure("belt_not_full_after_restock")
        log.warning("belt still not full after %d clicks: stash out of Full Rejuvs?", moved)
    bot.press("esc")
    bot.kill.sleep(0.5)
    log.info("restocked belt with %d potions", moved)
    if moved <= 0 and not slots:  # every stash potion slot came up empty
        state.save({**state.load(), "stash_rejuvs_empty": True})
        log.warning("stash is out of rejuvs; skipping restocks until logs/state.json says otherwise")
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


def _save_tooltip(bot: Controller, x: int, y: int) -> None:
    """Hover an inventory item and keep its tooltip (logs/loot/<time>.png): names unique rings."""
    import time

    bot.input.move(x, y)
    bot.kill.sleep(0.35)
    out = LOOT_CSV.parent / "loot"
    out.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out / f"{time.strftime('%Y%m%d-%H%M%S')}_{x}_{y}.png"), bot.capture.grab()[:, 400:1280])


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


def stowaway(bot: Controller, stash: bool = True) -> dict | None:
    """At the stash stop: Ctrl+click loot (runes, unique rings: anything outside Stephen's protected
    cells that isn't a key) into the stash, then drop key stacks beyond one (pickups add whole stacks;
    2026-10-26 eight full stacks had filled the inventory). Runes auto-route to the Runes tab; the rest
    goes to shared page 1. An extra key stack means the kept one is full, so keys_left becomes 12.
    `stash=False` (no stash nearby, e.g. the A4 spawn): keys only; None if there's loot for the stash."""
    from . import state
    from .vision.inventory import cell_center, runes_added

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
            bot.click(*scfg["shared_tab"])
            bot.kill.sleep(0.4)
            for c, r in inv["other"]:
                _save_tooltip(bot, *cell_center(c, r))
                _ctrl_click(bot, *cell_center(c, r))
            left = _scan_inventory(bot)["other"]
            done["stashed"] = len(inv["other"]) - len(left)
            bot.click(*scfg["runes_tab"])
            bot.input.move(640, 600)
            bot.kill.sleep(0.4)
            runes = runes_added(runes_before, bot.capture.grab())
            others = done["stashed"] - len(runes)
            _log_loot([f"{n} Rune" for n in runes] + ["item to shared tab"] * max(0, others))
            done["runes"] = runes
            if left:
                bot.save_failure("stowaway_left_items")
                log.warning("stowaway: %d item(s) stayed in the inventory (stash page full?): %s", len(left), left)
            bot.press("esc")
            bot.kill.sleep(0.4)
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
    return 1 if bot.find("a1_spawn.png", (120, 0, 560, 300), 0.75) else 3


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
