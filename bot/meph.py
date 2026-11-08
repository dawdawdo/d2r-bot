"""Mephisto on Durance of Hate Level 3: the classic moat trick from the dock.

Level 3 arrival -> 6 hops left along the walkway to the dock -> remember the dock's view (`ref`) ->
buffs -> hunt the Council near the dock (name bars) -> hop onto his platform to wake him -> back to
the dock by the view -> Blizzard him while he stands stuck at the far moat edge -> his name over an
empty bar = dead -> clear around the dock -> teleport to his body -> loot.

Built in tools/probe_level3.py (2026-11-01): 2 dock kills in a row at 97-100 % life; the live notes
are in docs/meph-navigation.md. Everything is screen-relative: hops are screen px from her
(640, 330); "the spot" is matched by view (bot.durance.view_offset), not by map position.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np

from .controller import BotError, GameSkipped
from .vision.namebar import name_bar

log = logging.getLogger(__name__)

CENTER = (640, 330)
WORLD_PER_PX = 1.1  # odometer world px per screen px of a teleport (Level 3 hops)
DOCK_HOPS = [(-350, -60)] * 6  # Level 3 arrival -> the dock (the walkway runs up-left)
WAKE_HOPS = [(-430, 50), (-300, -150)]  # dock -> his platform; he wakes, then back by the view
WAKE_WAIT = 3.0
PRESUME_DEAD_MISSES = 5  # search rounds without his bar after he was last seen below 30 %. At 10 she searched 2 min
                         # for a dead Meph (2026-11-03 18:24). In all logs he only came back after 1-2 misses
PRESUME_DEAD_LOW_MISSES = 4  # the same below 20 %: one volley finishes him, often unseen during the retreat hop
LOOT_SIGN_LOW = 0.5  # last seen below this + new loot labels on the ground = dead (one volley can take 50 %)
DROP_WAIT = 6.0
DEATH_THROES_S = 14.0  # s out of reach after his empty bar (hit at +11 s back on the spot, 15:01)
LOOT_X = (0, 1000)  # screen x (from the dock) of his body worth a trip (2 hops at most, checked)  # s from his last breath to the loot on the floor
DANGER_MP = 30  # mana % (= her Energy Shield) below which she leaves his reach to recover
SAFE_HOP = (350, 60)  # dock -> one hop back down the walkway (the way in: walkable, further from the moat)
# his screen x from the dock where his lightning can't reach her: kills had him at 20-400; at 400-480 her
# shield went 100 -> 3 % in ~2 s (a chicken and a death, 2026-11-01 22:17 / 22:20)
DOCK_SAFE_X = (0, 380)
RECOVER_MP, RECOVER_HP, RECOVER_S = 70, 80, 8.0
FLINCH_HP = 85  # life % that cuts a volley short (bursts of 400+ life in ~2 s)
# the south bank (Stephen's spot, his recorded view 206; Stephen 2026-11-02: "trap him on the bottom side of
# the moat ... a chance of avoiding the entire council"): dock -> 2 hops down-left, matched by view
SOUTH_HOPS = [(-364, 105)] * 2
SOUTH_VIEW = Path(__file__).parent / "assets" / "templates" / "meph_south_view.jpg"
SOUTH_WAKE = [(0, -300)]  # his platform is one hop north of the spot (woke him 3 of 3, 2026-11-01)
SOUTH_EXTRA_WAKE = (-350, -120)  # one more hop up-left from the dais (tried on every other wake)
SOUTH_RETREAT = (100, 180)  # between volleys / to recover: down-right, out of his reach
SOUTH_LURE = (-364, 105)  # one more hop down-left along the bank (the way the 2 hops came): drags him left
# where he can't reach her: 2026-11-02 13:46-14:50, stuck at x 360-400 (y 75-170): 6 kills at 97-99 % life;
# top centre (640-720, 20): 1 kill, 2 chickens (lightning bursts). Elsewhere she waits away for him to move
# (he usually walks left along the edge), and fights after STUCK_ROUNDS there anyway
SOUTH_SAFE_X = (280, 600)
SOUTH_NEVER_X = (600, 960)  # top centre: never fight there, stuck or not (chickens 14:01, 14:46, 15:13)
WAKE_GRID = [(x, y) for y in range(40, 560, 60) for x in range(80, 1240, 90)]  # all of the screen
STUCK_ROUNDS = 6  # rounds at one point (outside safe_x) after which he counts as stuck at the moat edge
NEVER_STUCK_ROUNDS = 8  # rounds (~4 s each) parked in never_x before giving up the game
# meph.fight_parked: since the respec he reached never_x in 8 of 41 fights and she killed him in none of them, the lure
# never rescued one. Those rules date from the old build (485 life, no BO), so fight him there and see
PARKED_FIGHT_ROUNDS = 3  # rounds seen in never_x before she fights him there
PARKED_GIVE_UP_ROUNDS = 12  # rounds fighting him there with no real damage: out of reach, new game
PARKED_MIN_DAMAGE = 0.05
CLEAR_SPOTS = [(780, 250), (520, 260), (720, 400)]  # Blizzard targets around her
# he shows at y 20-130 from either spot (2026-11-01/02 logs); lower rows cost ~15 s per missed search
MEPH_GRID = sorted([(x, y) for y in range(20, 190, 55) for x in range(80, 1200, 80)],
                   key=lambda p: (p[0] - 720) ** 2 + 4 * (p[1] - 50) ** 2)
WIDER_POINTS = 16  # of MEPH_GRID, nearest his last point: searched when he's not right there (~2 s). 110 of 246 kills
                  # had misses or waits and took 42 s, not 19 (2026-11-06); the full grid only came after 4 misses
# the Council: top band first (Wyand Voidbringer, Mana Burn, stands up-right of the dock), then the rest
HUNT_GRID = sorted([(x, y) for y in range(60, 520, 70) for x in range(100, 1200, 90)],
                   key=lambda p: (p[1] > 200, abs(p[0] - 760)))


def loot_labels(frame: np.ndarray, cfg: dict) -> list:
    """Item labels on the ground, except white ones: gold and keys drop from any monster she kills here."""
    from .vision.labels import find_labels

    kinds = {k: v for k, v in cfg["vision"]["labels"].items() if k != "white"}
    return find_labels(frame, kinds, ignore=cfg["vision"]["label_ignore"])


def new_labels(labels: list, base: list, tol: int = 40) -> list:
    """Labels that weren't there at the start of the fight (the view moves up to ~20 px between hops)."""
    return [a for a in labels if not any(abs(a.x - b.x) <= tol and abs(a.y - b.y) <= tol for b in base)]


class MephFight:
    """One fight from a remembered spot. `since_ref`: screen-px hops made since the spot was
    remembered, undone when the view is no help."""

    def __init__(self, bot, out: Path | None = None, say=log.info, retreat=None, safe_x=DOCK_SAFE_X,
                 wake_hop=None, verbose: bool = False, extra_wake=None,
                 never_x=None, lure=None, fight_parked=False) -> None:
        self.bot, self.out, self.say, self.verbose = bot, out, say, verbose
        self.lure = lure  # (dx, dy) hop to drag him toward safe_x when he parks in never_x
        # wake_hop: one (dx, dy) or a list of hops to his platform (the dock needs 2)
        if wake_hop is not None and not isinstance(wake_hop[0], (tuple, list)):
            wake_hop = [wake_hop]
        self.retreat, self.safe_x, self.wake_hop = retreat, safe_x, wake_hop
        self.extra_wake = extra_wake
        self.never_x = never_x
        self.fight_parked = fight_parked
        self.seen_at = 0.0  # time he was last seen awake (no wake hops onto his platform soon after)
        self.loot_base: list = []  # item labels on the ground when the fight began
        self.ref: np.ndarray | None = None
        self.since_ref: list = []
        self.last: tuple[int, int] | None = None  # where to look for Mephisto first
        self.seen: tuple[int, int] | None = None  # where he was last found (his body, for the loot)

    # -- frames -------------------------------------------------------------------------------------
    def snap(self, name: str) -> None:
        if self.out is not None:
            cv2.imwrite(str(self.out / f"{name}.jpg"), cv2.resize(self.bot.capture.grab(), (640, 360)))

    # -- moving -------------------------------------------------------------------------------------
    def tp(self, dx: float, dy: float, wait: float = 0.45) -> None:
        from .nav import in_play

        dx, dy = in_play(dx, dy)
        self.bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
        self.bot.sleep(wait)

    def remember(self) -> None:
        self.since_ref.clear()
        self.ref = self.bot.capture.grab()

    def away(self, dx: float, dy: float, wait: float = 0.45) -> None:
        """A hop that back_to may have to undo."""
        self.since_ref.append((dx, dy))
        self.tp(dx, dy, wait)

    def back_to(self, max_hops: int = 5, tol: float = 90, min_resp: float = 0.10) -> bool:
        # min_resp 0.10: the dock itself reads 0.12-0.3; at 0.15 a right answer (72 px off, 0.13) was
        # turned down and the next hop wandered off (2026-11-01 22:14 "pushed off the spot")
        """Teleport until this view matches the remembered spot. True once within `tol` world px."""
        from .durance import view_offset

        ok = False
        for k in range(max_hops + 1):
            off, resp = view_offset(self.ref, self.bot.capture.grab())
            dist = float(np.hypot(*off))
            self.say(f"back: off {off.round().tolist()} resp {resp:.2f} (hop {k})")
            if resp >= min_resp and dist <= tol:
                ok = True
                break
            if k == max_hops:
                break
            if resp < 0.08:  # the view is no help: undo the hops made since the spot (one hop at a time)
                back = -np.sum(self.since_ref, axis=0) if self.since_ref else np.array([430.0, -50.0])
                n = max(1, int(np.ceil(np.hypot(*back) / 420)))
                dx, dy = back / n
                if self.since_ref:
                    self.since_ref.append((dx, dy))
            else:
                scale = min(1.0, 450 / max(dist / WORLD_PER_PX, 1))
                dx, dy = -off[0] / WORLD_PER_PX * scale, -off[1] / WORLD_PER_PX * scale
            self.tp(dx, dy)
        self.since_ref.clear()
        return ok

    def on_spot(self, what: str) -> None:
        """'Teleport when struck' (her gear) throws her around: back to the spot first."""
        from .durance import view_offset

        def off_spot():
            off, resp = view_offset(self.ref, self.bot.capture.grab())
            return off, resp, resp < 0.1 or float(np.hypot(*off)) > 150  # resp 0.12-0.3 on the dock itself

        off, resp, bad = off_spot()
        if bad:  # read again: the dock view has a second match ~460 px up; one reading flips (2026-11-01 22:20)
            self.bot.sleep(0.15)
            off2, resp2, bad = off_spot()
            bad = bad and float(np.hypot(*(off - off2))) < 60
        if bad:
            self.say(f"{what}: off the spot ({off.round().tolist()}, resp {resp:.2f}) -> back")
            if not self.back_to():
                raise BotError("pushed off the spot")

    def in_danger(self) -> bool:
        return (self.bot.mp or 100) < DANGER_MP

    def recover(self, what: str) -> None:
        """Shield low: one hop back down the walkway, drink / regenerate, back to the spot."""
        bot = self.bot
        self.say(f"{what}: MP {bot.mp} HP {bot.hp} -> out of reach to recover")
        self.since_ref.clear()
        self.away(*(self.retreat or SAFE_HOP), wait=0.5)
        t0 = time.time()
        while time.time() - t0 < RECOVER_S and ((bot.mp or 0) < RECOVER_MP or (bot.hp or 0) < RECOVER_HP):
            bot.sleep(0.3)  # the guard drinks meanwhile
        if not self.back_to():
            raise BotError("couldn't get back after recovering")

    def wake(self) -> None:
        """Hop onto his platform (he wakes when she's near), wait, back to the spot."""
        bot, sk = self.bot, self.bot.cfg["hotkeys"]["skills"]
        self.since_ref.clear()
        hops = list(self.wake_hop)
        if getattr(self, "wakes", 0) % 2 == 1 and self.extra_wake:
            # the dais alone left him asleep 7 times in a row (2026-11-02 14:53-14:57; nobody on screen there):
            # every other try goes one hop further, up-left, where he comes from when he does wake
            hops.append(self.extra_wake)
        for dx, dy in hops:
            self.away(dx, dy)
        # standing there woke him 1 time in 4 (2026-11-02 13:5x): a Static Field hits what's around her
        self.snap(f"wake{getattr(self, 'wakes', 0)}")
        self.wakes = getattr(self, "wakes", 0) + 1
        bot.press(sk["static_field"])
        bot.click(*CENTER, "right", hover=0)
        bot.sleep(0.4)
        # still asleep 7 times in a row once (2026-11-02 14:35-14:40): look for him from up here, hit him once
        hit = self.first_name(WAKE_GRID, dwell=0.06)
        if hit and hit[1]["mephisto"]:
            self.say(f"wake: Mephisto seen at {hit[0]} from his platform -> one Blizzard")
            self.seen_at = time.time()
            bot.press(sk["blizzard"])
            bot.click(*hit[0], "right", hover=0)
            bot.sleep(0.4)
        else:
            self.say(f"wake: no Mephisto from his platform ({'a name' if hit else 'no names'})")
        bot.press(sk["teleport"])
        if len(hops) > len(self.wake_hop):  # the view can't be matched from up there (2 runs, 2026-11-02 15:03)
            ex, ey = hops[-1]
            self.away(-ex, -ey)
        bot.sleep(WAKE_WAIT)

    def step_away(self, wait: float) -> None:
        if not self.retreat:
            self.bot.sleep(wait)
            return
        self.since_ref.clear()
        self.away(*self.retreat, wait=wait)
        if not self.back_to():
            raise BotError("couldn't get back after the retreat")

    # -- looking ------------------------------------------------------------------------------------
    def first_name(self, pts, dwell: float = 0.06):
        for x, y in pts:
            if self.in_danger():  # a 12 s grid sweep while his lightning drains the shield: 2026-11-01 death
                return None
            self.bot.check()
            self.bot.input.move(x, y)
            self.bot.kill.sleep(dwell)
            nb = name_bar(self.bot.capture.grab())
            if nb is not None:
                return (x, y), nb
        return None

    def names_near(self, radius: int = 330, n: int = 20, stop_hp: float | None = None) -> list[tuple[int, int]]:
        """Points around her where a monster name shows. `stop_hp`: give up the sweep (it takes ~2 s) once life
        falls below this; the caller sees self.hurt."""
        hits = []
        self.hurt = False
        for r, k in ((radius, n), (radius // 2, n // 2)):
            for j in range(k):
                if stop_hp is not None and (self.bot.hp or 100) < stop_hp:
                    self.hurt = True
                    self.bot.input.move(1270, 590)
                    return hits
                a = 2 * np.pi * j / k
                x, y = int(640 + r * np.cos(a)), int(330 + 0.6 * r * np.sin(a))
                if not (60 < y < 560):
                    continue
                self.bot.check()
                self.bot.input.move(x, y)
                self.bot.kill.sleep(0.07)
                if name_bar(self.bot.capture.grab()) is not None:
                    hits.append((x, y))
        self.bot.input.move(1270, 590)
        return hits

    def ground_labels(self) -> list:
        """Item labels on screen with no name under the cursor (his name is label-colored too)."""
        bot = self.bot
        bot.input.move(1270, 590)
        bot.sleep(0.12)
        return loot_labels(bot.capture.grab(), bot.cfg)

    def loot_dropped(self) -> bool:
        """New non-white labels since the fight began. Alt may be off until there's something to tell by."""
        from .lk import ensure_labels_on

        self.bot.input.move(1270, 590)
        ensure_labels_on(self.bot)
        fresh = new_labels(self.ground_labels(), self.loot_base)
        if fresh:
            self.say(f"loot on the ground: {[(a.kind, a.x, a.y) for a in fresh[:4]]}")
        return bool(fresh)

    def find_meph(self) -> tuple[tuple[int, int], float] | None:
        """(point, life) where Mephisto's bar shows: near his last point if known, then wider, else the grid."""
        if self.last:
            lx, ly = self.last
            near = [(min(1260, max(20, lx + dx)), min(560, max(8, ly + dy)))
                    for dy in (0, 25, -12, 50) for dx in (0, -40, 40, -80, 80)]
            wider = sorted(MEPH_GRID, key=lambda p: (p[0] - lx) ** 2 + 4 * (p[1] - ly) ** 2)[:WIDER_POINTS]
            searches = [near, wider]
        else:
            searches = [MEPH_GRID]
        for pts in searches:
            hit = self.first_name(pts, dwell=0.1)
            if hit and hit[1]["mephisto"]:
                return hit[0], hit[1]["life"]
        return None

    # -- fighting -----------------------------------------------------------------------------------
    def hunt(self, limit: float = 60, min_mp: float = 30) -> bool:
        """Kill what's near the spot until a full scan finds no name (True). Mephisto is left alone."""
        bot, sk = self.bot, self.bot.cfg["hotkeys"]["skills"]
        t0, rnd = time.time(), 0
        try:
            while time.time() - t0 < limit:
                self.on_spot("hunt")
                if self.in_danger():
                    self.recover("hunt")
                    continue
                if (bot.mp or 0) < min_mp:
                    bot.sleep(0.3)
                    continue
                rnd += 1
                hit = self.first_name(HUNT_GRID)
                if hit is None or hit[1]["mephisto"]:
                    self.say(f"hunt round {rnd}: {'Mephisto' if hit else 'no names'} HP {bot.hp} MP {bot.mp}")
                    bot.input.move(1270, 590)
                    return True
                (x, y), nb = hit
                bot.press(sk["blizzard"])
                for _ in range(3):
                    bot.click(x, y, "right", hover=0)
                    bot.sleep(0.5)
                    if self.in_danger():
                        break
                bot.press(sk["teleport"])
                now = name_bar(bot.capture.grab())
                self.say(f"hunt round {rnd}: name at ({x}, {y}) life {nb['life']:.2f} -> "
                         f"{'gone' if now is None else round(now['life'], 2)} HP {bot.hp} MP {bot.mp}")
        finally:
            bot.press(sk["teleport"])
        return False

    def kill(self, limit: float = 180, min_mp: float = 40) -> bool:
        """Blizzard Mephisto from the spot until he's dead (True)."""
        from .town import refresh_warcries

        bot, sk = self.bot, self.bot.cfg["hotkeys"]["skills"]
        t0, low, misses, rnd = time.time(), 1.0, 0, 0
        prev, still, lured = None, 0, False  # rounds he has stood at the same point outside the band
        never_rounds, parked_rounds, parked_life = 0, 0, 1.0
        self.loot_base = self.ground_labels()
        try:
            while time.time() - t0 < limit:
                self.on_spot("kill")
                if self.in_danger():
                    self.recover("kill")
                    continue
                if (bot.mp or 0) < min_mp:
                    bot.sleep(0.3)
                    continue
                rnd += 1
                if self.verbose:
                    self.snap(f"kill{rnd:02d}")
                found = self.find_meph()
                if found is None:
                    misses += 1
                    self.say(f"kill round {rnd}: Mephisto not found (low {low:.2f}, misses {misses})")
                    if low < LOOT_SIGN_LOW and self.loot_dropped():
                        self.say(f"kill round {rnd}: gone at {low:.2f} and loot dropped: dead")
                        return True
                    # low and gone, nothing visible dropped (the filter hides most, or he died off screen): he
                    # also walks off along the moat edge and back (2026-11-01 21:55: out left at 0.17, a 0.24
                    # "kill" looted nothing), so a short absence doesn't count
                    if (low < 0.3 and misses >= PRESUME_DEAD_MISSES) or (low < 0.2 and misses >= PRESUME_DEAD_LOW_MISSES):
                        self.say("kill: low and long gone: presumed dead")
                        return True
                    if (bot.hp or 100) < 90 or (misses % 3 == 0 and low >= 0.3):
                        # something else is on her: Council walking in along the walkway killed her while
                        # this loop only looked for him (2026-11-01 22:38)
                        self.hunt(limit=20)
                    if misses >= 4:
                        self.last = None  # he walked off: full search next time
                    # every miss (a search round ~5 s), but not right after he was seen: hopping onto his platform
                    # with him awake there killed her (2026-11-02 15:16)
                    if self.wake_hop and low >= 1.0 and time.time() - self.seen_at > 30:
                        self.say("kill: hop to his platform to wake him")
                        self.wake()
                        if not self.back_to():
                            raise BotError("couldn't get back from his platform")
                        continue
                    bot.sleep(0.8)
                    continue
                misses, (self.last, life) = 0, found
                self.seen_at = time.time()
                self.seen = self.last
                low = min(low, life)
                if life <= 0:  # his name over an empty bar: dying
                    self.say(f"kill round {rnd}: Mephisto at {self.last} has no life left: dead")
                    return True
                still = still + 1 if prev is not None and abs(self.last[0] - prev[0]) <= 40 and abs(
                    self.last[1] - prev[1]) <= 40 else 0
                prev = self.last
                # stuck elsewhere on the far edge: he stood at (360, 75) for 3 min at full life, never coming
                # round (2026-11-02 13:46, south bank): 3 rounds in one place = stuck, fight him there
                never = self.never_x is not None and self.never_x[0] <= self.last[0] <= self.never_x[1]
                never_rounds += int(never)
                fight_here = False
                if never and self.fight_parked and never_rounds >= PARKED_FIGHT_ROUNDS:
                    if not parked_rounds:
                        parked_life = life
                        self.say(f"kill round {rnd}: Mephisto parked at {self.last} (life {life:.2f}): fighting him there")
                    parked_rounds += 1
                    if parked_rounds >= PARKED_GIVE_UP_ROUNDS and parked_life - life < PARKED_MIN_DAMAGE:
                        raise GameSkipped(f"Mephisto at {self.last}: {parked_rounds} rounds, no damage: new game")
                    never, fight_here = False, True  # the normal fight below, retreats and all
                if never and still >= STUCK_ROUNDS and self.lure and not lured:
                    # parked on the never side: walk him along the moat edge toward the safe side (he follows
                    # her along it), then come back and see where he stops
                    lured, still = True, 0
                    self.say(f"kill round {rnd}: Mephisto parked at {self.last}: lure {self.lure}")
                    self.since_ref.clear()
                    self.away(*self.lure, wait=4.0)
                    if not self.back_to():
                        raise BotError("couldn't get back after the lure")
                    continue
                if never and still >= NEVER_STUCK_ROUNDS:
                    # parked at the top centre: he stayed there 3+ min at full life (2026-11-02 23:01) and we
                    # never fight there. His spot differs per game: a new game is quicker than the timeout
                    raise GameSkipped(f"Mephisto stuck at {self.last} (top centre, never fought there): new game")
                if not fight_here and not (self.safe_x[0] <= self.last[0] <= self.safe_x[1]) and (
                        never or still < STUCK_ROUNDS or not self.retreat):
                    self.say(f"kill round {rnd}: Mephisto at {self.last} (life {life:.2f}) is in reach: waiting away")
                    self.since_ref.clear()
                    self.away(*(self.retreat or SAFE_HOP), wait=3.0)
                    if not self.back_to():
                        raise BotError("couldn't get back after waiting away")
                    continue
                refresh_warcries(bot)
                bot.press(sk["blizzard"])
                hit = False
                for _ in range(3):
                    bot.click(*self.last, "right", hover=0)
                    bot.sleep(0.5)
                    nb = name_bar(bot.capture.grab())
                    if nb and nb["mephisto"]:
                        low = min(low, nb["life"])
                        if nb["life"] <= 0:  # died mid-volley (2026-11-01 22:23: then 2 min of searching)
                            self.say(f"kill round {rnd}: Mephisto at {self.last} has no life left: dead")
                            return True
                    if (bot.hp or 100) < FLINCH_HP or self.in_danger():
                        hit = True
                        break
                bot.press(sk["teleport"])
                self.say(f"kill round {rnd}: Mephisto at {self.last} life {life:.2f} (low {low:.2f}) "
                         f"HP {bot.hp} MP {bot.mp}")
                if self.retreat:
                    self.step_away(1.5 * (2 if hit else 1))
        finally:
            bot.press(sk["teleport"])
        return False

    def clear(self, limit: float = 45, min_mp: float = 50) -> bool:
        """Blizzard around her until a hover sweep finds no monster name (True) or `limit` s pass."""
        bot, sk = self.bot, self.bot.cfg["hotkeys"]["skills"]
        t0, rnd, targets = time.time(), 0, list(CLEAR_SPOTS)
        try:
            while time.time() - t0 < limit:
                while (bot.mp or 0) < min_mp and time.time() - t0 < limit:
                    bot.sleep(0.3)
                bot.press(sk["blizzard"])
                for x, y in targets[:3]:
                    bot.click(x, y, "right", hover=0)
                    bot.sleep(0.45)
                bot.press(sk["teleport"])
                bot.sleep(0.6)
                hits = self.names_near()
                rnd += 1
                self.say(f"clear round {rnd}: {len(hits)} name hovers {hits[:4]} HP {bot.hp} MP {bot.mp}")
                if not hits:
                    return True
                cx, cy = np.mean(hits, axis=0).astype(int)
                targets = [(int(cx), int(cy))] + list(CLEAR_SPOTS)
        finally:
            bot.press(sk["teleport"])
        return False


def to_dock(bot, odo=None) -> None:
    """Level 3 arrival -> the dock (fixed hops; the walkway is the same every game)."""
    from .nav import hop

    for dx, dy in DOCK_HOPS:
        if odo is not None:
            hop(bot, odo, dx, dy)
        else:
            bot.click(CENTER[0] + dx, CENTER[1] + dy, "right", hover=0)
            bot.sleep(0.45)


def fight_from_dock(fight: MephFight) -> bool:
    """At the dock: remember it, buffs, Council hunt, wake him, back, kill. True = Mephisto dead."""
    from .town import cast_buffs, cast_warcries

    bot = fight.bot
    fight.remember()
    cast_buffs(bot)
    cast_warcries(bot)
    fight.say(f"dock: buffs HP {bot.hp} MP {bot.mp}")
    fight.hunt()
    for dx, dy in WAKE_HOPS:
        fight.away(dx, dy)
    bot.sleep(WAKE_WAIT)
    if not fight.back_to():
        fight.say("back to the dock: not exact; the kill loop corrects it")
    fight.snap("dock")
    return fight.kill()


def fight_from_south(fight: MephFight) -> bool:
    """Dock -> the south bank (no Council hunt: they stay up by the dock) -> wake him -> kill from across
    the moat with hit-and-run volleys. True = Mephisto dead."""
    from .town import cast_buffs, cast_warcries

    bot = fight.bot
    for dx, dy in SOUTH_HOPS:
        fight.tp(dx, dy)
    fight.ref = cv2.imread(str(SOUTH_VIEW))
    fight.since_ref.clear()  # matched 0.32-0.41 there on 2026-11-01 (the dock reads 0.12-0.3)
    if not fight.back_to():
        raise BotError("south bank: view not matched")
    cast_buffs(bot)
    cast_warcries(bot)
    fight.say(f"south bank: buffs HP {bot.hp} MP {bot.mp}")
    fight.wake()
    if not fight.back_to():
        fight.say("back to the south bank: not exact; the kill loop corrects it")
    fight.snap("dock")
    return fight.kill()


def loot_meph(fight: MephFight, retry: bool = False, t_dead: float | None = None) -> list[str]:
    """After the kill: clear what's near the dock, teleport over to where he died, pick up."""
    from .lk import loot

    bot = fight.bot
    if t_dead is None:
        t_dead = time.time()
        # out of reach for his death throes, every time: lightning flies round the spot for 10+ s after the
        # empty bar (2026-11-02 14:33 dead 3 s after, 15:01 chicken 12 s after, his soul still rising)
        fight.say(f"after the kill: HP {bot.hp} MP {bot.mp} -> out of reach for {DEATH_THROES_S:.0f} s")
        fight.since_ref.clear()
        fight.away(*(fight.retreat or SAFE_HOP), wait=0.5)
        while time.time() - t_dead < DEATH_THROES_S or (
                time.time() - t_dead < DEATH_THROES_S + RECOVER_S and ((bot.mp or 0) < RECOVER_MP or (bot.hp or 0) < RECOVER_HP)):
            bot.sleep(0.3)
        if not fight.back_to():
            raise BotError("couldn't get back after his death throes")
        if bot.cfg["meph"].get("clear_before_loot", False):  # the check at his body below still finds company
            if not fight.clear(limit=25):
                fight.clear(limit=20)  # names still round the spot: they're at his body too (2026-11-08 HP 96 -> 5 there)
    if fight.seen is None or not (LOOT_X[0] <= fight.seen[0] <= LOOT_X[1]):
        # far along the moat edge: 2 hops into the unknown met lightning there and she died (2026-11-01 22:11)
        fight.say(f"loot: he died at {fight.seen}, out of one safe hop: skipping")
        return []
    x, y = fight.seen
    fight.since_ref.clear()
    dx, dy = x - CENTER[0], y + 40 - CENTER[1]  # the bar shows over his body: land just below
    n = max(1, int(np.ceil(np.hypot(dx, dy) / 420)))
    for _ in range(n):  # 2 hops when he died far left; check after each (the 22:11 death was out there)
        fight.away(dx / n, dy / n, wait=0.6)
        if fight.in_danger():
            fight.say(f"loot: MP {bot.mp} on the way -> back to the dock")
            fight.back_to()
            return []
    bot.wait_still(timeout=2)
    hp0 = bot.hp or 100
    near = fight.names_near(radius=280, n=12, stop_hp=min(75, hp0 - 20))
    if fight.hurt:  # Council fire took 96 -> 5 % during this sweep (2026-11-08 15:48): out first, ask later
        fight.say(f"loot: HP {hp0} -> {bot.hp} at his body -> back to the spot")
        fight.back_to()
        if retry or (bot.hp or 0) < 60:
            return []
        fight.hunt(limit=30)
        return loot_meph(fight, retry=True, t_dead=t_dead)
    if near and not retry:  # his Council / leftovers (2026-11-02 13:51): kill them from the spot, try again
        fight.say(f"loot: monsters at his body {near[:3]} -> back to the spot, hunt, try again")
        fight.back_to()
        fight.hunt(limit=30)
        return loot_meph(fight, retry=True, t_dead=t_dead)
    if near:
        # still company after the hunt: grab what shows and go (2026-11-03 23:10 left the drop for a few leftovers;
        # Stephen: Blizzaga may die, and these kills are what we're here for)
        picked = [] if fight.in_danger() else loot(bot, take_all=True, max_picks=4)
        fight.say(f"loot: monsters at his body {near[:3]}: grabbed {picked} -> back to the spot")
        fight.back_to()
        return picked
    fight.snap("dead")
    # the drop comes at the end of his death animation (2026-11-01 21:44: she stood on a dying body, found nothing)
    bot.sleep(max(0.0, DROP_WAIT - (time.time() - t_dead)))
    picked = [] if fight.in_danger() else loot(bot, take_all=True)
    if fight.in_danger():
        fight.say(f"loot: MP {bot.mp} HP {bot.hp} at his body -> back to the dock")
        fight.back_to()
    fight.snap("loot")
    if not picked:  # full size: why a kill looted nothing can't be told from the small snaps (2026-11-03: a ring left)
        bot.save_failure("meph_loot_empty")
    fight.say(f"loot: {picked}")
    return picked
