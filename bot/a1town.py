"""Act 1 town services (Rogue Encampment) for tasks whose games start and end in Act 1 (Andariel): stash, Akara (heal,
potions), Kashya (merc), Charsi (repair). Stephen 2026-11-23: Andariel runs should never go to Act 3.

The town automap names the NPCs and the stash: a label over a white cross that follows the NPC around. The automap is
1/8 scale and centred on her own marker, so a label's offset from that marker x 8 is its offset in the world view.
walk_to() steps toward a label, re-reading the automap after every step (NPCs wander; the spawn spot varies), and
talk() clicks the NPC once close (a hover scan around the spot if the first click misses).
"""
from __future__ import annotations

import logging
import math

import cv2
import numpy as np

from .config import ROOT
from .controller import Controller
from .nav import CENTER

log = logging.getLogger(__name__)

TEMPLATES = ROOT / "bot" / "assets" / "templates"
MAP_PLAYER = (642, 353)  # her blue chevron on the automap (full-res px; 2026-11-23 frames)
MAP_SCALE = 8.0          # world px per automap px (bot/durance.py AUTOMAP_SCALE)
LABEL_TO_MARK = 23       # an NPC's cross sits this far below its label's centre
LABEL_MIN = 0.8          # map_<name>.png: 0.94-1.00 on its label, <= 0.53 elsewhere (0.70: half covered by another)
LABEL_MIN_OF = {"kashya": 0.65}  # she stands by Warriv and Cain, whose labels cover hers ("Deckard Cainshya": 0.70-0.75;
                                 # 12:09 not found 58 px from the stash); nothing else scored over 0.59 in 20 town frames
NAMES = ("akara", "kashya", "charsi", "stash")
STEP_MAX = (480, 220)    # px from the screen centre for one walk click (inside bot/town.py WALK_BOX)
BODY_UP = 45             # an NPC's clickable body is this far above the ground spot the cross marks
SHORT = 150              # walk clicks stop this far short of the target: a click on an NPC talks to her

_tpl: dict[str, np.ndarray] = {}


def _template(name: str) -> np.ndarray:
    if name not in _tpl:
        _tpl[name] = cv2.imread(str(TEMPLATES / f"map_{name}.png"))
    return _tpl[name]


LABEL_BOX = 300  # px around her marker: labels show within ~1,200 world px (150 automap px); farther matches are
                 # noise (2026-11-23: a "stash" 3,164 px off, then 149 px the next read)


def map_labels(frame: np.ndarray, names=NAMES) -> dict[str, tuple[int, int, float]]:
    """Automap labels in view: name -> (label centre x, y, score)."""
    x0, y0 = max(0, MAP_PLAYER[0] - LABEL_BOX), max(0, MAP_PLAYER[1] - LABEL_BOX)
    crop = frame[y0:MAP_PLAYER[1] + LABEL_BOX, x0:MAP_PLAYER[0] + LABEL_BOX]
    out = {}
    for n in names:
        t = _template(n)
        r = cv2.matchTemplate(crop, t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if mx >= LABEL_MIN_OF.get(n, LABEL_MIN):
            out[n] = (x0 + loc[0] + t.shape[1] // 2, y0 + loc[1] + t.shape[0] // 2, float(mx))
    return out


def world_offset(name: str, label: tuple[int, int, float]) -> tuple[float, float]:
    """The labelled thing's offset from her in the world view (px), from its automap label."""
    mx, my = label[0], label[1] + LABEL_TO_MARK  # the stash's label sits over it the same way (her at the chest:
    # its label 23 px above her own marker, 2026-11-23)
    return (mx - MAP_PLAYER[0]) * MAP_SCALE, (my - MAP_PLAYER[1]) * MAP_SCALE


def _step(dx: float, dy: float) -> tuple[int, int]:
    """A walk click toward (dx, dy), shortened to fit STEP_MAX."""
    k = min(1.0, STEP_MAX[0] / max(1e-6, abs(dx)), STEP_MAX[1] / max(1e-6, abs(dy)))
    return int(CENTER[0] + dx * k), int(CENTER[1] + dy * k)


def town_automap(bot: Controller) -> np.ndarray:
    """The automap up, judged by its info text (top right) only: in town the line-pixel test of
    durance.automap_shown fires on the campfire stones (2026-11-23: 'shown' with no map up). Closes only what is
    really up first (the game menu, an NPC menu, a trade/stash panel): a blind Esc opened the game menu and the
    retries left it up (17:35)."""
    from .controller import BotError
    from .durance import map_text_open
    from .vision.inventory import inventory_open

    for attempt in range(4):
        f = bot.capture.grab()
        if map_text_open(f):
            return f
        if bot.observe() == "esc_menu" or menu_up(bot, f) or inventory_open(f):
            bot.press("esc")
            esc_cleared(bot)
            continue
        bot.press("tab")
        for _ in range(10):  # Proton shows the map late (up to ~2 s on GLaDOS)
            bot.kill.sleep(0.25)
            f = bot.capture.grab()
            if map_text_open(f):
                return f
    bot.save_failure("a1_automap_wont_show")
    raise BotError("automap won't show (Act 1)")


def esc_cleared(bot: Controller, timeout: float = 2.0, poll: float = 0.2) -> bool:
    """After an Esc: wait for the game menu / NPC menu / inventory to go before anything presses Esc again. A re-check
    0.5 s later still saw the game menu (Proton, its fade), so the next Esc reopened it: 4 tries ran out with it up and
    Andariel runs failed "automap won't show" (2026-11-25 04:16, 04:27)."""
    from .vision.inventory import inventory_open

    t_end = bot.clock() + timeout
    while True:
        bot.kill.sleep(poll)
        if bot.observe() != "esc_menu" and not menu_up(bot, bot.frame) and not inventory_open(bot.frame):
            return True
        if bot.clock() >= t_end:
            return False


def town_map_off(bot: Controller) -> None:
    from .durance import map_text_open

    if map_text_open(bot.capture.grab()):
        bot.press("tab")
        bot.kill.sleep(0.35)


def npc_menu(bot: Controller, frame: np.ndarray | None = None) -> tuple[int, int] | None:
    """An NPC menu is up: its first line, TALK (blue), top-left."""
    from .vision.screen import match_score

    t = _tpl.get("dlg_talk")
    if t is None:
        t = _tpl["dlg_talk"] = cv2.imread(str(TEMPLATES / "dlg_talk.png"))
    score, loc = match_score(bot.capture.grab() if frame is None else frame, t, (0, 0, 1280, 560))
    return loc if score >= 0.8 else None


MENU_SIGNS = ("dlg_talk", "dlg_cancel", "npc_kashya", "npc_akara", "npc_charsi")


def menu_up(bot: Controller, frame: np.ndarray | None = None) -> bool:
    """Any NPC menu up: TALK blue (the default line) is not enough: with another line highlighted it's white
    (2026-11-23 13:36: Kashya's menu with Hire lit after a revive; Tab did nothing and the walk failed)."""
    from .vision.screen import match_score

    f = bot.capture.grab() if frame is None else frame
    for n in MENU_SIGNS:
        t = _tpl.get(n)
        if t is None:
            t = _tpl[n] = cv2.imread(str(TEMPLATES / f"{n}.png"))
        if match_score(f, t, (0, 0, 1280, 560))[0] >= 0.8:
            return True
    return False


def close_npc(bot: Controller) -> None:
    """Esc only when an NPC menu is up: a blind Esc opens the game menu, and on top of an NPC a missed menu click
    talks to her instead (2026-11-23 probe: Kashya's dialog kept coming back during save & exit)."""
    if menu_up(bot):
        bot.press("esc")
        bot.kill.sleep(0.35)


AKARA_TO_STASH = (-1824, -480)  # her label -> the stash; she keeps by her tent (2 frames; a third 100 px off)
AKARA_TO_WP = (-812, -353)       # her label -> the waypoint (2 frames within 4 px)
# fallback labels while the target's isn't drawn (labels show within ~1,200 px of her): (label, offset to walk toward)
VIA = {"stash": (("kashya", (0, 0)), ("akara", AKARA_TO_STASH)),
       "charsi": (("stash", (0, 0)), ("kashya", (0, 0)), ("akara", AKARA_TO_STASH)),
       "kashya": (("stash", (0, 0)), ("akara", AKARA_TO_STASH)),  # she keeps near the stash
       "akara": (("kashya", (0, 0)), ("stash", (-AKARA_TO_STASH[0], -AKARA_TO_STASH[1]))),
       "wp": (("akara", AKARA_TO_WP), ("kashya", (0, 0)))}
# 2026-11-23 11:59: from Akara's tent neither Kashya's nor the stash's label showed: no stash, no revive
VIA_NEAR = 300  # walk this close to a VIA point, then look for the target's label again
ANCHOR = {"wp": ("stash", (1012, 127))}  # no label of its own: the waypoint from the stash's (2 frames agree within
                                        # 8 px, 2026-11-23)


def walk_to(bot: Controller, name: str, near: float = 200, steps: int = 12) -> tuple[float, float] | None:
    """Walk until `name` is within `near` px (isometric distance). Returns its offset from her (view px), or None.
    Each click aims SHORT px short of the target, so it doesn't land on the NPC (that talks to her). Labels show only
    within ~1,200 px of her (2026-11-23: Charsi and the stash not drawn from Akara's spot): until the target's shows,
    walk toward a VIA label (Kashya stands by the stash, Charsi is beyond it). Walls (walks are straight lines): a
    step without progress slides off at +-60 degrees, toward a VIA label too (2026-11-23: stuck 810 px from the
    stash on the way to Charsi)."""
    last = None  # (goal, dx, dy) of the last step
    missing = blocked = 0
    for i in range(steps):
        f = town_automap(bot)
        look, (ax, ay) = ANCHOR.get(name, (name, (0, 0)))
        labs = map_labels(f, (look,) + tuple(v for v, _ in VIA.get(name, ())))
        if look in labs:
            goal = name
            dx, dy = world_offset(look, labs[look])
            dx, dy = dx + ax, dy + ay
        else:
            via, voff = next(((v, o) for v, o in VIA.get(name, ()) if v in labs), (None, (0, 0)))
            if via is None:
                missing += 1
                log.info("%s: no automap label (%d)", name, missing)
                if missing >= 3:
                    return None
                bot.click(*_step(0, 200 if missing == 1 else -200))  # off whoever hides it / into unrevealed map
                bot.kill.sleep(1.2)
                continue
            goal = via
            dx, dy = world_offset(via, labs[via])
            dx, dy = dx + voff[0], dy + voff[1]
        d = math.hypot(dx, 2 * dy)
        if last is not None and last[0] == goal and math.hypot(dx - last[1], dy - last[2]) > 1500:
            log.info("%s: %s read %.0f px away, a jump: reading again", name, goal, d)  # 11-23: 349 -> 3157 -> 171
            last = None
            continue
        log.info("%s: %s%.0f px away (%.0f, %.0f)", name, "" if goal == name else f"no label yet; {goal} ", d, dx, dy)
        if goal == name and d <= near:
            return dx, dy
        if goal != name and d <= VIA_NEAR:  # by the VIA label and still no target label: look around
            missing += 1
            if missing >= 3:
                return None
            bot.click(*_step(0, 200 if missing == 1 else -200))
            bot.kill.sleep(1.2)
            last = None
            continue
        stuck = last is not None and last[0] == goal and abs(dx - last[1]) + abs(dy - last[2]) < 30
        if npc_menu(bot, f) is not None:
            close_npc(bot)  # a walk click talked to someone
        elif stuck:
            blocked += 1
            a = math.atan2(dy, dx) + math.radians(60 if blocked % 2 else -60) * (1 + (blocked - 1) // 2 * 0.5)
            log.info("%s: no progress; detour %d", name, blocked)
            bot.click(*_step(400 * math.cos(a), 400 * math.sin(a)))
            bot.kill.sleep(1.0)
            last = None
            continue
        last = (goal, dx, dy)
        k = max(0.0, (d - SHORT) / d)
        bot.click(*_step(dx * k, dy * k))
        bot.kill.sleep(1.0 if d > 400 else 0.7)
    return None


def dialog_open(bot: Controller, name: str) -> tuple[int, int] | None:
    """The NPC's dialog: its name at the top (npc_<name>.png; any NPC menu until that template exists).
    Returns the match's top-left."""
    if (TEMPLATES / f"npc_{name}.png").exists():
        return bot.find(f"npc_{name}.png", region=(0, 0, 1280, 500), threshold=0.8)
    return npc_menu(bot)


def talk(bot: Controller, name: str, off: tuple[float, float]) -> tuple[int, int] | None:
    """Click the NPC (offset from walk_to, then fresh from the automap before each retry: they wander, and the merc
    may stand in front; 2026-11-23 Akara moved ~80 px between the read and the click); hover-scan around her last
    spot if three clicks miss. Returns the dialog's match."""
    from .town import _name_points

    for attempt in range(3):
        if attempt:
            f = town_automap(bot)
            lab = map_labels(f, (name,)).get(name)
            if lab is not None:
                off = world_offset(name, lab)
        town_map_off(bot)
        loc = dialog_open(bot, name)
        if loc is not None:  # a walk click already talked to her
            return loc
        close_npc(bot)
        x, y = int(CENTER[0] + off[0]), int(CENTER[1] + off[1] - BODY_UP)
        bot.click(min(max(x, 30), 1250), min(max(y, 50), 550))
        # she walks there first: from ~350 px the dialog came after a fixed 1.5 s, and the retry's automap closed
        # it (2026-11-23 12:03: three "misses" with Akara reached each time)
        wait = 1.2 + math.hypot(off[0], 2 * off[1]) / 250
        t = 0.0
        while t < wait:
            bot.kill.sleep(0.3)
            t += 0.3
            loc = dialog_open(bot, name)
            if loc is not None:
                return loc
        log.info("%s: click at (%d, %d) missed (try %d)", name, x, y, attempt + 1)
    close_npc(bot)
    region = (max(30, x - 160), max(50, y - 120), 320, 260)
    for attempt, (hx, hy) in enumerate(_name_points(bot, region)):
        if attempt >= 5:
            break
        bot.click(hx, hy)
        bot.kill.sleep(1.5)
        loc = dialog_open(bot, name)
        if loc is not None:
            return loc
        close_npc(bot)  # someone else's dialog (or nothing)
    bot.save_failure(f"a1_{name}_not_found")
    return None


# --- the services ------------------------------------------------------------------------------------------------
RESTOCK_AFTER = 3   # belt potions drunk since the last refill that send her to Akara even with no column empty
NEAR = 350          # close enough: a click on an NPC or the stash walks her the rest of the way (closer, the walk
                    # clicks landed on Warriv beside the stash: his menu has Go East, 2026-11-23)
STASH_UP = 10       # the chest's body above the spot its label marks
AKARA = {"healing_potion": (395, 337), "mana_potion": (395, 375), "antidote": (395, 148)}  # Misc tab (2026-11-23)
ANTIDOTE_COLS = 2   # belt columns of antidotes for Andariel's poison (Stephen 2026-11-23); 1 healing + 1 mana left
INV0, INV_P = (867.0, 350.0), 37.8  # inventory grid (bot/vision/inventory.py)
LINE_PITCH = 24     # NPC menu lines (Kashya, Akara 2026-11-23)
RESURRECT_W = 72    # px: RESURRECT (9 letters) is the menu's widest line; CANCEL ~58


def _menu_line(menu: tuple[int, int], n: int) -> tuple[int, int]:
    """Screen point of menu line n (0 = TALK) from TALK's top-left."""
    return menu[0] + 20, menu[1] + 6 + LINE_PITCH * n


def _line_widths(frame: np.ndarray, menu: tuple[int, int], lines: int = 5) -> list[int]:
    """Width of the white text on each menu line below TALK (the gold box border doesn't count)."""
    out = []
    for n in range(1, lines + 1):
        y = menu[1] + LINE_PITCH * n
        band = frame[max(0, y - 2):y + 14, max(0, menu[0] - 70):menu[0] + 130].astype(int)
        b, g, r = band[..., 0], band[..., 1], band[..., 2]
        white = (b > 150) & (g > 150) & (r > 150) & (abs(r - b) < 45)
        cols = np.nonzero(white.any(axis=0))[0]
        out.append(int(cols[-1] - cols[0]) if len(cols) else 0)
    return out


def _wait_stash(bot: Controller, timeout: float = 3.6) -> bool:
    from .town import stash_shown

    t = 0.0
    while t < timeout:
        bot.kill.sleep(0.3)
        t += 0.3
        if stash_shown(bot):
            return True
    return False


def open_stash_a1(bot: Controller) -> bool:
    """Walk to the stash's automap label, click the chest (hover for its tooltip if that misses), wait for the panel."""
    from .town import _name_points, stash_shown

    if stash_shown(bot):
        return True
    for attempt in range(2):  # from Akara's end of town it's ~1,600 px with walls: 12 steps fell short (11-23 11:14)
        off = walk_to(bot, "stash", near=NEAR, steps=20)
        if off is None:
            continue
        town_map_off(bot)
        close_npc(bot)
        x, y = int(CENTER[0] + off[0]), int(CENTER[1] + off[1] - STASH_UP)
        bot.click(x, y)
        if _wait_stash(bot):
            return True
        close_npc(bot)  # an NPC in front of it took the click
        for k, (hx, hy) in enumerate(_name_points(bot, (max(30, x - 120), max(50, y - 90), 240, 180))):
            if k >= 4:
                break
            bot.click(hx, hy)
            if _wait_stash(bot):
                return True
            close_npc(bot)
    bot.save_failure("a1_stash_not_opened")
    log.warning("Act 1 stash didn't open")
    return False


def revive_merc_a1(bot: Controller, retry: bool = True) -> bool:
    """Kashya: Resurrect (the widest line of her menu while the merc is dead). One more try when the click didn't take
    (2026-11-25 21:42: the menu still open on Resurrect, the merc still dead; ~1 in 10 revives over 11-24/25, and
    each one cost a run)."""
    from .town import merc_alive, resurrect_result

    off = walk_to(bot, "kashya", near=NEAR, steps=16)
    if off is None or talk(bot, "kashya", off) is None:
        log.warning("Kashya not found; merc not revived")
        return False
    bot.kill.sleep(0.3)
    f = bot.capture.grab()
    menu = npc_menu(bot, f)
    widths = _line_widths(f, menu) if menu else []
    n = max(range(len(widths)), key=lambda i: widths[i]) + 1 if widths else 0
    if not widths or widths[n - 1] < RESURRECT_W:
        close_npc(bot)
        if menu and merc_alive(bot):  # Talk / Hire / Cancel: he's alive (his portrait was late), nothing to do
            log.info("Kashya: no Resurrect line and his portrait is up: the merc is alive")
            return True
        bot.save_failure("a1_kashya_no_resurrect")
        log.warning("Kashya: no Resurrect line (widths %s)", widths)
        return False
    bot.click(*_menu_line(menu, n))
    bot.kill.sleep(1.5)
    bot.press("esc")
    bot.kill.sleep(0.5)
    if retry and not merc_alive(bot, tries=6):
        bot.save_failure("a1_resurrect_click_missed")
        log.info("Kashya: merc still dead after the Resurrect click; asking her again")
        close_npc(bot)
        return revive_merc_a1(bot, retry=False)
    return resurrect_result(bot, "Kashya")


def _spare_mana_to_antidotes(bot: Controller) -> None:
    """A second antidote column from a spare mana column (the shield seldom needs them): drink it empty before the
    trade (belt keys do nothing with the trade window up). 14:36: one column (4) ran out after the stairs dose and two
    cures, and the poison took her to a chicken. Mana potions cost little; success first (Stephen 2026-11-23)."""
    from .vision.orbs import belt_kinds

    keys = bot.cfg["hotkeys"]["potions"]

    def kinds():
        return belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"])

    k = kinds()
    if not (k.count("antidote") < ANTIDOTE_COLS and k.count("mp") >= 2 and None not in k):
        return
    i = len(k) - 1 - k[::-1].index("mp")  # the rightmost mana column
    for _ in range(6):
        if kinds()[i] is None:
            break
        bot.press(keys[i])
        bot.kill.sleep(0.5)
    log.info("emptied a spare mana column for antidotes: belt %s", kinds())


def akara_stop(bot: Controller, buy: bool) -> bool:
    """Akara: talking heals; with `buy`, Trade and potions into the belt (healing + mana, like the Ormus stop)."""
    if buy:
        _spare_mana_to_antidotes(bot)

    off = walk_to(bot, "akara", near=NEAR)
    if off is None or talk(bot, "akara", off) is None:
        log.warning("Akara not found")
        return False
    log.info("healed by Akara")
    if not buy:
        close_npc(bot)
        return True
    menu = npc_menu(bot)
    if menu is None:
        return True
    bot.click(*_menu_line(menu, 1))  # Talk / Trade / Cancel
    from .vision.inventory import inventory_open

    for _ in range(8):
        bot.kill.sleep(0.3)
        # her tab strip varies (Weapons / Weapons / Misc, or Weapons / Misc: the Ormus template missed it twice,
        # 2026-11-23 18:18 and 22:12, with the window open); the inventory panel beside it is always there
        if (bot.find("trade_ormus_misc.png", region=(0, 0, 640, 140), threshold=0.8) is not None
                or inventory_open(bot.capture.grab())):
            bot.kill.sleep(0.3)
            return restock_at_akara(bot)
    bot.save_failure("a1_akara_trade_not_opened")
    bot.press("esc")
    bot.kill.sleep(0.4)
    return False


def _antidote_cols(kinds: list) -> int:
    """Empty belt columns to fill with antidotes: up to ANTIDOTE_COLS, never at the cost of the last healing or mana
    column (11:23 2026-11-23: the emptied healing column became antidotes and left her with none); the mixed buy
    after this fills the reserved ones."""
    reserve = (0 if any(k in ("hp", "rejuv") for k in kinds) else 1) + (0 if "mp" in kinds else 1)
    return max(0, min(ANTIDOTE_COLS - kinds.count("antidote"), kinds.count(None) - reserve))


def buy_antidotes(bot: Controller) -> int:
    """With Akara's trade open: fill empty belt columns up to ANTIDOTE_COLS with antidotes. Vendors put them in the
    inventory, never the belt (2026-11-23, plain and shift buys alike), so: 4 a column into the inventory, then
    shift+left-click each (into the antidote column with room, else the leftmost empty one). One left over is drunk
    (never stashed). Returns how many reached the belt."""
    from .vision.inventory import protected_cells, scan as inv_scan
    from .vision.orbs import belt_kinds

    cols = _antidote_cols(belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"]))
    if cols <= 0:
        return 0
    key_tpl = cv2.imread(str(TEMPLATES / "inv_key.png"))
    prot = protected_cells(bot.cfg["inventory"]["protected"])

    def empty() -> set:
        bot.input.move(640, 600)
        bot.kill.sleep(0.6)  # Proton shows a new item late
        return set(inv_scan(bot.capture.grab(), key_tpl, prot)["empty"])

    before = empty()
    n = min(4 * cols, len(before))
    for _ in range(n):
        bot.click(*AKARA["antidote"], "right")
        bot.kill.sleep(0.5)
    bought = sorted(before - empty())
    if n and not bought:  # nothing arrived: no gold on her (2026-11-23 11:52: two revives took it all). The next
        from . import state  # stash stop withdraws (town_stop -> withdraw_gold)

        log.warning("Akara: no antidote bought (no gold?): withdrawing at the next stash stop")
        state.save({**state.load(), "gold_needed": True})
        return 0

    def cell(c: int, r: int) -> tuple[int, int]:
        return int(INV0[0] + INV_P * c + INV_P / 2), int(INV0[1] + INV_P * r + INV_P / 2)

    for c, r in bought:
        bot.input.key_down("shift")
        bot.kill.sleep(0.05)
        bot.click(*cell(c, r))
        bot.kill.sleep(0.05)
        bot.input.key_up("shift")
        bot.kill.sleep(0.4)
    left = sorted(set(bought) - empty())
    for c, r in left:  # the belt had no room for it: drink it rather than let the stowaway stash it
        bot.click(*cell(c, r), "right")
        bot.kill.sleep(0.6)
    log.info("Akara: %d antidote(s) bought, %d into the belt, belt %s", len(bought), len(bought) - len(left),
             belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"]))
    return len(bought) - len(left)


def _inv_cells(bot: Controller) -> set:
    """Empty inventory cells (the trade window shows the inventory where it always is)."""
    from .vision.inventory import protected_cells, scan as inv_scan

    t = _tpl.get("inv_key")
    if t is None:
        t = _tpl["inv_key"] = cv2.imread(str(TEMPLATES / "inv_key.png"))
    bot.input.move(640, 600)
    bot.kill.sleep(0.6)  # Proton shows a new item late
    return set(inv_scan(bot.capture.grab(), t, protected_cells(bot.cfg["inventory"]["protected"]))["empty"])


def _inv_point(c: int, r: int) -> tuple[int, int]:
    return int(INV0[0] + INV_P * c + INV_P / 2), int(INV0[1] + INV_P * r + INV_P / 2)


def _buy(bot: Controller, kind: str, n: int, until_spill: bool = False) -> int:
    """Plain right-click buys of Akara's healing/mana potion: they go to the belt column of that kind with room, else
    the leftmost empty one. until_spill: stop (and drink it) when one lands in the inventory. Returns buys made."""
    before = _inv_cells(bot) if until_spill else set()
    for i in range(n):
        bot.click(*AKARA[kind], "right")
        bot.kill.sleep(0.5)
        if until_spill:
            spilled = before - _inv_cells(bot)
            if spilled:
                for c, r in spilled:  # drink it: never stashed (Stephen 2026-11-13)
                    bot.click(*_inv_point(c, r), "right")
                    bot.kill.sleep(0.6)
                left = before - _inv_cells(bot)
                log.info("Akara: %s topped up with %d, the next one spilled (drunk%s)", kind, i, "" if not left else
                         f", NOT: {sorted(left)}")
                return i
    if until_spill:
        log.info("Akara: %s topped up with %d, no spill", kind, n)
    return n


def restock_at_akara(bot: Controller) -> bool:
    """With Akara's trade open: the belt as 1+ healing, 1+ mana and up to ANTIDOTE_COLS antidote columns.
    Empty columns get exactly 4 of their kind (healing first, then mana, then antidotes), so nothing overflows into
    a column meant for another kind; with no empty column left, healing then mana are topped up until one spills
    (drunk). 2026-11-23 14:13: the antidotes took the only empty column, the half-used healing column was never
    topped up, and it ran dry in the fight (chicken, "belt is empty")."""
    from .vision.orbs import belt_kinds

    def kinds():
        return belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"])

    k = kinds()
    if not any(x in ("hp", "rejuv") for x in k) and None in k:
        _buy(bot, "healing_potion", 4)
        k = kinds()
    if "mp" not in k and None in k:
        _buy(bot, "mana_potion", 4)
        k = kinds()
    buy_antidotes(bot)
    k = kinds()
    while None in k:  # still empty ones (antidotes at their max): healing and mana alternately
        _buy(bot, "healing_potion" if sum(x == "hp" for x in k) <= sum(x == "mp" for x in k) else "mana_potion", 4)
        k2 = kinds()
        if k2 == k:
            break  # nothing changed (no gold?)
        k = k2
    if None not in k:
        _buy(bot, "healing_potion", 4, until_spill=True)
        _buy(bot, "mana_potion", 4, until_spill=True)
    from .town import drink_inventory_potions

    drink_inventory_potions(bot, "Akara")  # never a bought potion left for the stowaway (Stephen 2026-11-24)
    log.info("Akara: belt %s", kinds())
    bot.potions_used = 0
    bot.press("esc")
    bot.kill.sleep(0.5)
    return True


def charsi_repair(bot: Controller) -> bool:
    """Charsi: Trade/Repair, Repair All."""
    if not (TEMPLATES / "npc_charsi.png").exists():  # never a line click on an unconfirmed menu (Warriv: Go East)
        log.warning("no npc_charsi.png yet: no Act 1 repair")
        return False
    off = walk_to(bot, "charsi", near=NEAR, steps=20)
    if off is None or talk(bot, "charsi", off) is None:
        log.warning("Charsi not found; no repair")
        return False
    menu = npc_menu(bot)
    if menu is None:
        return False
    bot.click(*_menu_line(menu, 1))  # Talk / Trade/Repair / Imbue / Cancel
    for _ in range(10):
        bot.kill.sleep(0.3)
        if bot.find("trade_repair_all.png", region=(300, 460, 120, 100), threshold=0.8) is not None:
            bot.click(*bot.cfg["town"]["hratli"]["repair_all"])
            bot.kill.sleep(1.0)
            bot.press("esc")
            bot.kill.sleep(0.5)
            log.info("repaired at Charsi")
            return True
    bot.save_failure("a1_charsi_trade_not_opened")
    bot.press("esc")
    bot.kill.sleep(0.4)
    return False


def _log_merc_portrait(bot: Controller) -> None:
    """Debug (2026-11-24): the portrait check says dead but Kashya shows no Resurrect, 5 times overnight. Log the score
    and keep the corner, to see what his portrait looked like then."""
    try:
        import time

        from .vision.screen import match_score

        f = bot.capture.grab()
        x, y, w, h = bot.cfg["town"]["merc_region"]
        t = cv2.imread(str(TEMPLATES / "merc_portrait.png"))
        score, _ = match_score(f, t, (x, y, w, h))
        out = ROOT / "logs" / "merc_portrait"
        out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / f"{time.strftime('%m%d-%H%M%S')}_{score:.2f}.png"), f[0:120, 0:200])
        log.info("merc portrait score %.2f (alive at >= 0.85)", score)
    except Exception as e:  # debugging only
        log.debug("merc portrait debug: %s", e)


def town_stop(bot: Controller, cfg: dict, repair: bool = False, stow: bool = False) -> bool:
    """Everything due, in the Rogue Encampment: heal, stash (loot, gold for a revive, deposit), Kashya, Akara's
    potions, Charsi. True if anything walked her off (the caller starts a fresh game)."""
    from . import state
    from .tasks.tunnels import empty_columns
    from .town import (close_stash, deposit_gold, heal_with_belt, merc_alive, needs_heal, stowaway, withdraw_gold)

    walked = False
    hp_low = needs_heal(bot)
    if hp_low and heal_with_belt(bot, cfg["town"]["heal_below_pct"]):
        log.info("healed with belt potions (HP %.0f%%)", bot.hp or 0)
        hp_low = needs_heal(bot)
    used = getattr(bot, "potions_used", 0)
    belt = empty_columns(bot) >= 1 or used >= RESTOCK_AFTER  # 16:49: a fight began on a half-used belt (only the
    # bottom row shows) and ran dry: no healing, no antidote; her death burst then chickened her with the loot down
    if hp_low or belt:
        log.info("Act 1: Akara (%s)", ", ".join(w for w, on in (("heal", hp_low), ("potions", belt)) if on))
        walked = True
        akara_stop(bot, buy=belt)
    if stow or state.load().get("gold_needed"):
        walked = True
        if withdraw_gold(bot):
            bot.merc_wait, bot.merc_fails = 0, 0
        if stow:
            stowaway(bot)
        deposit_gold(bot)
        close_stash(bot)
    elif deposit_gold(bot) is not None:  # carrying the max: only then does it open the stash
        walked = True
        close_stash(bot)
    if getattr(bot, "merc_revive", True) and not merc_alive(bot) and not (bot.kill.sleep(1.5) or merc_alive(bot)):
        # (a second look: his portrait comes late after a game loads; 00:38 a walk to Kashya with him alive)
        _log_merc_portrait(bot)
        log.info("merc is dead -> Kashya")
        walked = True
        ok = revive_merc_a1(bot)
        if not ok and state.load().get("gold_needed") and withdraw_gold(bot):
            # not enough gold: take it from the stash now and try again, rather than losing a run (14:38)
            close_stash(bot)
            ok = revive_merc_a1(bot)
        if ok:
            bot.merc_fails = 0
        else:
            from .run import MERC_MAX_FAILS, MERC_PAUSE_RUNS, MERC_RETRY_RUNS

            bot.merc_fails = getattr(bot, "merc_fails", 0) + 1
            bot.merc_revive = False
            bot.merc_wait = MERC_PAUSE_RUNS if bot.merc_fails >= MERC_MAX_FAILS else MERC_RETRY_RUNS
    if repair:
        walked = True
        if charsi_repair(bot):
            st = {k: v for k, v in state.load().items() if k != "repair_due"}
            state.save({**st, "runs_since_repair": 0, "runs_since_dur_check": 0})
    if walked and back_to_wp(bot):
        return False  # the waypoint is in view: no fresh game (~25 s) needed
    return walked


def back_to_wp(bot: Controller) -> bool:
    """After the stops: walk back to the waypoint (found from the stash's label) so the run goes on in this game.
    True when it's in view."""
    from .town import close_stash

    close_stash(bot)
    close_npc(bot)
    off = walk_to(bot, "wp", near=300)
    town_map_off(bot)
    ok = False
    for _ in range(3 if off is not None else 0):  # the map closes late: 13:11 missed it 143 px away
        bot.kill.sleep(0.3)
        if bot.find("a1_wp.png", (0, 0, 1280, 600), 0.6) is not None:
            ok = True
            break
    log.info("back at the waypoint: %s", "yes" if ok else "no (fresh game)")
    return ok
