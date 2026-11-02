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

from .controller import BotError
from .vision.namebar import name_bar

log = logging.getLogger(__name__)

CENTER = (640, 330)
WORLD_PER_PX = 1.1  # odometer world px per screen px of a teleport (Level 3 hops)
DOCK_HOPS = [(-350, -60)] * 6  # Level 3 arrival -> the dock (the walkway runs up-left)
WAKE_HOPS = [(-430, 50), (-300, -150)]  # dock -> his platform; he wakes, then back by the view
WAKE_WAIT = 3.0
DROP_WAIT = 6.0  # s from his last breath to the loot on the floor
FLINCH_HP = 85  # life % that cuts a volley short (bursts of 400+ life in ~2 s)
CLEAR_SPOTS = [(780, 250), (520, 260), (720, 400)]  # Blizzard targets around her
MEPH_GRID = sorted([(x, y) for y in range(20, 430, 55) for x in range(80, 1200, 80)],
                   key=lambda p: (p[0] - 720) ** 2 + 4 * (p[1] - 50) ** 2)
# the Council: top band first (Wyand Voidbringer, Mana Burn, stands up-right of the dock), then the rest
HUNT_GRID = sorted([(x, y) for y in range(60, 520, 70) for x in range(100, 1200, 90)],
                   key=lambda p: (p[1] > 200, abs(p[0] - 760)))


class MephFight:
    """One fight from a remembered spot. `since_ref`: screen-px hops made since the spot was
    remembered, undone when the view is no help."""

    def __init__(self, bot, out: Path | None = None, say=log.info, retreat=None, safe_x=(0, 1280),
                 wake_hop=None, verbose: bool = False) -> None:
        self.bot, self.out, self.say, self.verbose = bot, out, say, verbose
        self.retreat, self.safe_x, self.wake_hop = retreat, safe_x, wake_hop
        self.ref: np.ndarray | None = None
        self.since_ref: list = []
        self.last: tuple[int, int] | None = None  # where Mephisto was last hovered

    # -- frames -------------------------------------------------------------------------------------
    def snap(self, name: str) -> None:
        if self.out is not None:
            cv2.imwrite(str(self.out / f"{name}.jpg"), cv2.resize(self.bot.capture.grab(), (640, 360)))

    # -- moving -------------------------------------------------------------------------------------
    def tp(self, dx: float, dy: float, wait: float = 0.45) -> None:
        self.bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
        self.bot.sleep(wait)

    def remember(self) -> None:
        self.since_ref.clear()
        self.ref = self.bot.capture.grab()

    def away(self, dx: float, dy: float, wait: float = 0.45) -> None:
        """A hop that back_to may have to undo."""
        self.since_ref.append((dx, dy))
        self.tp(dx, dy, wait)

    def back_to(self, max_hops: int = 5, tol: float = 90, min_resp: float = 0.15) -> bool:
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

        off, resp = view_offset(self.ref, self.bot.capture.grab())
        if resp < 0.1 or float(np.hypot(*off)) > 150:  # resp 0.12-0.3 on the dock itself
            self.say(f"{what}: off the spot ({off.round().tolist()}, resp {resp:.2f}) -> back")
            if not self.back_to():
                raise BotError("pushed off the spot")

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
            self.bot.check()
            self.bot.input.move(x, y)
            self.bot.kill.sleep(dwell)
            nb = name_bar(self.bot.capture.grab())
            if nb is not None:
                return (x, y), nb
        return None

    def names_near(self, radius: int = 330, n: int = 20) -> list[tuple[int, int]]:
        hits = []
        for r, k in ((radius, n), (radius // 2, n // 2)):
            for j in range(k):
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

    def find_meph(self) -> tuple[tuple[int, int], float] | None:
        """(point, life) where Mephisto's bar shows: near his last point if known, else the grid."""
        if self.last:
            lx, ly = self.last
            pts = [(min(1260, max(20, lx + dx)), min(560, max(8, ly + dy)))
                   for dy in (0, 25, -12, 50) for dx in (0, -40, 40, -80, 80)]
        else:
            pts = MEPH_GRID
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
                bot.press(sk["teleport"])
                now = name_bar(bot.capture.grab())
                self.say(f"hunt round {rnd}: name at ({x}, {y}) life {nb['life']:.2f} -> "
                         f"{'gone' if now is None else round(now['life'], 2)} HP {bot.hp} MP {bot.mp}")
        finally:
            bot.press(sk["teleport"])
        return False

    def kill(self, limit: float = 180, min_mp: float = 40) -> bool:
        """Blizzard Mephisto from the spot until he's dead (True)."""
        bot, sk = self.bot, self.bot.cfg["hotkeys"]["skills"]
        t0, low, misses, rnd = time.time(), 1.0, 0, 0
        try:
            while time.time() - t0 < limit:
                self.on_spot("kill")
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
                    if low < 0.3 and misses >= 3:  # last seen nearly dead and gone: dead, or he walked off
                        if self.last is None:  # the full grid found nothing either (2026-11-01 21:40: a
                            return True  # 0.24 "kill" looted nothing; the empty-bar rule is the sure one)
                        self.say("kill: low and gone: a full search before calling it")
                        self.last = None
                        continue
                    if misses >= 4:
                        self.last = None  # he walked off: full search next time
                    if self.wake_hop and low >= 1.0 and misses % 2 == 0:
                        self.say("kill: hop to his platform to wake him")
                        self.since_ref.clear()
                        self.away(*self.wake_hop, wait=WAKE_WAIT)
                        if not self.back_to():
                            raise BotError("couldn't get back from his platform")
                        continue
                    bot.sleep(0.8)
                    continue
                misses, (self.last, life) = 0, found
                low = min(low, life)
                if life <= 0:  # his name over an empty bar: dying
                    self.say(f"kill round {rnd}: Mephisto at {self.last} has no life left: dead")
                    return True
                if not (self.safe_x[0] <= self.last[0] <= self.safe_x[1]):
                    self.say(f"kill round {rnd}: Mephisto at {self.last} (life {life:.2f}) is too close: waiting")
                    self.step_away(3.0)
                    continue
                bot.press(sk["blizzard"])
                hit = False
                for _ in range(3):
                    bot.click(*self.last, "right", hover=0)
                    bot.sleep(0.5)
                    nb = name_bar(bot.capture.grab())
                    if nb and nb["mephisto"]:
                        low = min(low, nb["life"])
                    if (bot.hp or 100) < FLINCH_HP:
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
    from .town import cast_buffs

    bot = fight.bot
    fight.remember()
    cast_buffs(bot)
    fight.say(f"dock: buffs HP {bot.hp} MP {bot.mp}")
    fight.hunt()
    for dx, dy in WAKE_HOPS:
        fight.away(dx, dy)
    bot.sleep(WAKE_WAIT)
    if not fight.back_to():
        fight.say("back to the dock: not exact; the kill loop corrects it")
    fight.snap("dock")
    return fight.kill()


def loot_meph(fight: MephFight) -> list[str]:
    """After the kill: clear what's near the dock, teleport over to where he died, pick up."""
    from .lk import loot

    bot = fight.bot
    t_dead = time.time()
    fight.clear(limit=25)
    if fight.last is not None:
        x, y = fight.last
        dx, dy = x - CENTER[0], y + 40 - CENTER[1]  # the bar shows over his body: land just below the hover
        n = max(1, int(np.ceil(np.hypot(dx, dy) / 420)))
        for _ in range(n):
            fight.tp(dx / n, dy / n, wait=0.5)
    bot.wait_still(timeout=2)
    fight.snap("dead")
    # the drop comes at the end of his death animation (2026-11-01 21:44: she stood on a dying body, found nothing)
    bot.sleep(max(0.0, DROP_WAIT - (time.time() - t_dead)))
    picked = loot(bot)
    if not picked:
        bot.sleep(2.0)
        picked = loot(bot)
    fight.snap("loot")
    fight.say(f"loot: {picked}")
    return picked
