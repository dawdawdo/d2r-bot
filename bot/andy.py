"""Andariel fight (Catacombs Level 4): from the stairs into her lair, find her by her name bar, Blizzard her from a
distance (Glacial Spike while Blizzard cools down), teleport away when she gets close, loot where she died.

Found live 2026-11-22 (tools/andy_probe.py): the stairs room opens west through a door (3 hops left); from there,
up-right hops lead toward her throne (red carpet, pillars), and she walks out to meet you. Her name bar was under
the cursor 150-300 px up-left of Blizzaga after "-320,0,3;300,-150,6". Hell: cold resist 66 % (not immune), fire -50 %,
poison attacks; Dark Ones, Dark Shamans (they raise the Dark Ones) and Ghouls all around.
"""
from __future__ import annotations

import logging
import math
import time

import numpy as np

from .controller import BotError
from .nav import CENTER, TP_SETTLE, frame_lag, in_play
from .vision.namebar import name_bar

log = logging.getLogger(__name__)

ROUTE = "-320,0,3;300,-150,2"  # screen px hops from the Level 4 arrival: through the door, then toward her throne
RING = [(r, k) for r, k in ((420, 16), (260, 12), (140, 8))]  # hover rings around Blizzaga for name bars
BLIZZARD_CD = 1.8  # s (config hotkeys.attack comment)
TOO_CLOSE = 400    # iso px (screen dy counts double): one hop back. 520 made nearly every sighting "too close" (the
                   # view reaches ~660 up/down) and she hopped instead of casting (03:54: 3 runs, never hit her)
STATIC_RANGE = 300  # iso px: Static Field's reach around Blizzaga (cast twice when she walks into it; Stephen 2026-11-22:
                   # "static field a couple of times at the beginning, then teleport to where the merc can tank")
STATICS = 0  # off: in the MF set (no Kira's resists) the two Statics up close let her poison take 91 -> 2 % (11-23 07:31)
LOST_DEAD = 0.40   # her life when last seen, below which "gone for 3 sweeps" counts as dead
RETREAT_HP = 70    # % life: two hops out of her reach, let potions / the shield catch up


def iso_dist(x: float, y: float) -> float:
    """Ground distance of a screen point from Blizzaga: the view is isometric, a screen px up/down is ~2 on the ground
    (22:02: her bar 252 px straight up read "too close" at 400 and two hops took her out of view)."""
    return math.hypot(x - CENTER[0], 2 * (y - CENTER[1]))


GRID = [(x, y) for y in range(90, 560, 70) for x in range(120, 1180, 90)]  # last resort: the whole view (~6 s)


def hops(bot, route: str) -> None:
    bot.press(bot.cfg["hotkeys"]["skills"]["teleport"])  # after a Blizzard / Glacial Spike the right-click casts that
    bot.kill.sleep(0.1)                                  # (2026-11-22 21:58: 40 s "hopping" in place at the barrels)
    for seg in route.split(";"):
        dx, dy, n = (int(v) for v in seg.split(","))
        dx, dy = in_play(dx, dy)
        for _ in range(n):
            bot.check()
            bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
            bot.sleep(TP_SETTLE + frame_lag(bot) + 0.15)


class AndyFight:
    def __init__(self, bot, say=log.info) -> None:
        self.bot, self.say = bot, say
        self.sk = bot.cfg["hotkeys"]["skills"]
        self.last: tuple[int, int] | None = None  # screen point where her bar last showed
        self.life = 1.0
        self.blizz_at = 0.0
        self.cries_at = getattr(bot, "cries_at", 0.0) or 0.0
        self.seen_dead = False
        self.threat: tuple[int, int] | None = None  # the last monster seen (retreat from it when hurt)
        self.wide = False  # add the whole-view grid to the sweep
        self.statics = 0  # Static Fields cast on her so far
        self.since_her = 0  # sweeps since her bar last showed
        self.come_back: tuple[float, float] | None = None  # unit vector back toward her after a life retreat
        self.offset = np.zeros(2)  # rough screen-px displacement from the fight spot (where the route ends)
        self.backed_at = 0.0  # last keep-away hop
        self.retreat_at = 0.0

    # -- finding her ------------------------------------------------------------------------------
    def _points(self):
        if self.last:
            lx, ly = self.last
            for dy in (0, 30, -25, 60):
                for dx in (0, -45, 45, -90, 90):
                    yield min(1240, max(40, lx + dx)), min(560, max(60, ly + dy))
        for r, k in RING:
            for j in range(k):
                a = 2 * np.pi * j / k
                x, y = int(CENTER[0] + r * np.cos(a)), int(CENTER[1] + 0.6 * r * np.sin(a))
                if 60 < y < 560:
                    yield x, y
        if self.wide:  # she was seen and lost (or never seen for a while): the whole view
            yield from sorted(GRID, key=lambda p: math.dist(p, self.last or CENTER))

    def find(self) -> tuple[tuple[int, int], float, bool] | None:
        """(point, life, is_her) of the first monster name under the cursor: her if she's anywhere on the sweep,
        else the first other monster seen (her Dark Ones swarm Blizzaga while she looks: 2026-11-22 21:29, 5 s sweeps
        with nothing cast, 100 -> 34 %). Monsters get Blizzard too, so the sweep clears the way."""
        bot = self.bot
        other = None
        for i, (x, y) in enumerate(self._points()):
            if i % 6 == 0:
                bot.check()
            bot.input.move(x, y)
            bot.kill.sleep(0.05)
            nb = name_bar(bot.capture.grab())
            if nb is None:
                continue
            if nb.get("andariel"):
                return (x, y), nb["life"], True
            if other is None:
                other = ((x, y), nb["life"], False)
                if i >= 12:  # well into the sweep with no sign of her: hit what's here now
                    break
        return other

    # -- moving -----------------------------------------------------------------------------------
    def hop(self, dx: float, dy: float) -> None:
        """One teleport by screen offset (dx, dy); `offset` keeps a rough count of where she is from the fight spot."""
        dx, dy = in_play(dx, dy)
        self.bot.press(self.sk["teleport"])
        self.bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
        self.bot.sleep(TP_SETTLE + frame_lag(self.bot) + 0.1)
        self.offset += np.array([dx, dy]) * 1.17  # landings ~1.17x the click offset (nav.HOP_GAIN); blocked hops overcount

    def away_from(self, x: float, y: float, dist: float = 380) -> None:
        """One hop directly away from screen point (x, y)."""
        self.say(f"away from ({x}, {y})")
        v = np.array([CENTER[0] - x, CENTER[1] - y], float)
        n = float(np.hypot(*v)) or 1.0
        self.hop(*(v / n * dist))

    def refresh_cries(self) -> None:
        from .town import cast_warcries

        if time.time() - self.cries_at > self.bot.cfg["hotkeys"].get("warcry_refresh_s", 75):
            cast_warcries(self.bot)
            self.cries_at = time.time()

    # -- the fight --------------------------------------------------------------------------------
    def kill(self, limit: float = 150) -> bool:  # 120 ran out with her at 22 % (2026-11-22 22:10)
        bot, sk = self.bot, self.sk
        t0, misses, casts, snap_at = time.time(), 0, 0, 0.0
        out = None
        try:
            from .config import ROOT

            out = ROOT / "logs" / "andy" / time.strftime("%m%d-%H%M%S")
            out.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        end = t0 + limit
        self.her_at = 0.0
        self.minions = 0
        try:
            while time.time() < end or (time.time() < t0 + limit + 60 and time.time() - self.her_at < 12):
                # past the limit only while she's in the fight (05:19: first seen as the 150 s ran out)
                bot.check()
                if (getattr(self, "antidote_rounds", ANTIDOTE_ROUNDS) < ANTIDOTE_ROUNDS
                        and time.time() - self.antidote_at > ANTIDOTE_EVERY and time.time() - self.her_at < 5):
                    self.antidote_rounds += 1
                    self.antidote_at = time.time()
                    antidotes(bot, "still fighting her")
                if out is not None and time.time() - snap_at > 4:  # for review: what the fight looked like
                    import cv2

                    cv2.imwrite(str(out / f"{time.time() - t0:05.1f}_hp{bot.hp or 0:.0f}.jpg"),
                                cv2.resize(bot.capture.grab(), None, fx=0.5, fy=0.5))
                    snap_at = time.time()
                self.refresh_cries()
                threat = self.last or self.threat
                if (bot.hp or 100) < RETREAT_HP and threat and time.time() - self.retreat_at > 2.5:
                    self.say(f"HP {bot.hp:.0f}%: away from {threat}")
                    if self.last or threat:  # the way back (00:56: retreated at her 37 % and never found her again)
                        tx, ty = self.last or threat
                        v = np.array([tx - CENTER[0], ty - CENTER[1]], float)
                        n = float(np.hypot(*v)) or 1.0
                        self.come_back = (v[0] / n, v[1] / n)
                    self.away_from(*threat)
                    self.away_from(*threat)
                    self.last = self.threat = None
                    self.retreat_at = time.time()
                    bot.sleep(0.6)
                    continue
                hit = self.find()
                self.say(f"find: {hit} HP {bot.hp} MP {bot.mp}")
                self.since_her = 0 if (hit and hit[2]) else self.since_her + 1
                if self.life <= LOST_DEAD and self.since_her >= 3:
                    # a dead Andariel has no bar to hover: last seen low and gone for 3 sweeps = dead (2026-11-22
                    # 23:38: 1.00 -> 0.21 in 4 s, then never seen again; the fight ran out its clock without looting)
                    self.seen_dead = True
                    self.say(f"her bar last read {self.life:.2f} and is gone for 3 sweeps: dead")
                    return True
                if hit is None and self.come_back and (bot.hp or 0) >= 80:
                    # life is back after a retreat from her: one hop back the way we came
                    ux, uy = self.come_back
                    self.come_back = None
                    self.hop(ux * 380, uy * 380)
                    self.say("back toward her after the retreat")
                    continue
                if hit is None:
                    misses += 1
                    self.wide = misses >= 2  # two empty sweeps: next one covers the whole view
                    if self.life <= 0.06 and casts:  # her bar was nearly empty and now it's gone: dead
                        self.seen_dead = True
                        return True
                    if misses % 3 == 0:  # nothing in view: one hop toward her throne
                        self.toward_throne()
                    continue
                misses = 0
                (x, y), life, her = hit
                self.minions = 0 if her else self.minions + 1
                if (not her and self.minions >= MINION_STREAK
                        and time.time() - max(self.her_at, t0) > HER_LOST_S):
                    # only minions for a while: she's elsewhere (with the merc kept alive by antidotes he tanks her
                    # out of view; 2026-11-23 11:20-11:45 five of six fights ran out never seeing her). Same step
                    # as an empty sweep
                    self.minions = 0
                    self.say(f"minions only, her not seen for {time.time() - max(self.her_at, t0):.0f} s")
                    self.toward_throne()
                    continue
                self.threat = (x, y)
                if her:
                    self.last, self.life = (x, y), life
                    self.her_at = time.time()
                    if life <= 0.0:
                        self.seen_dead = True
                        self.say("Andariel's bar is empty: dead")
                        return True
                elif self.life <= 0.06 and casts:
                    self.seen_dead = True
                    return True
                self.wide = not her and misses == 0 and casts > 0 and self.life < 1.0  # keep looking for her too
                if her and self.statics < STATICS and iso_dist(x, y) < STATIC_RANGE:
                    # she walked into reach: Static Field twice (a share of her current life each), then two hops away
                    # so the merc holds her and Blizzard does the rest from the edge of the screen
                    for _ in range(STATICS - self.statics):
                        bot.press(sk["static_field"])
                        bot.click(CENTER[0], CENTER[1] - 30, "right", hover=0)
                        bot.sleep(0.45)
                        self.statics += 1
                    nb = name_bar(bot.capture.grab())
                    self.say(f"static x{self.statics}: her life {life:.2f} -> {nb['life'] if nb else '?'}")
                    self.away_from(x, y)
                    self.away_from(x, y)
                    self.last = None
                    continue
                if her and iso_dist(x, y) < TOO_CLOSE and time.time() - self.backed_at > 2.0:
                    # (before the Statics too: waiting for Static range let her poison land, 03:32). Not twice in a
                    # row within 2 s: a hop blocked by the walls leaves her where she was, and then casting is better
                    self.backed_at = time.time()
                    if time.time() - self.blizz_at >= BLIZZARD_CD:  # one on her before going: every sighting hurts
                        bot.press(sk["blizzard"])
                        bot.click(x, y, "right", hover=0)
                        self.blizz_at = time.time()
                        casts += 1
                        bot.sleep(0.3)
                    self.away_from(x, y)
                    # she's now about one hop further along the line from Blizzaga to her
                    v = np.array([x - CENTER[0], y - CENTER[1]], float)
                    v = v / (float(np.hypot(*v)) or 1.0) * 380 * 1.17
                    self.last = (int(np.clip(x + v[0], 40, 1240)), int(np.clip(y + v[1] * 0.6, 60, 560)))
                    continue
                # aim a little in front of her: she walks toward Blizzaga
                ax, ay = int(x + 0.15 * (CENTER[0] - x)), int(y + 0.15 * (CENTER[1] - y))
                if time.time() - self.blizz_at >= BLIZZARD_CD:
                    bot.press(sk["blizzard"])
                    self.blizz_at = time.time()
                else:
                    bot.press(sk["glacial_spike"])
                bot.click(ax, ay, "right", hover=0)
                casts += 1
                bot.sleep(0.35)
                if casts % 6 == 0:
                    self.say(f"cast {casts}: her life {life:.2f}, HP {bot.hp} MP {bot.mp}")
        finally:
            bot.press(sk["teleport"])
            bot.input.move(1270, 590)
        return False

    def toward_throne(self) -> None:
        """One hop toward her throne. From the fight spot (by the barrels) she comes from straight above: every kill
        so far had her bar at (639, 78); up-right runs into the barrels and the brazier (2026-11-22 23:22: 2.5 min,
        never seen). Drifted off (retreats, minions): back toward the fight spot first."""
        far = float(np.hypot(*self.offset))
        if far > 300:
            v = -self.offset / far * min(far, 380)
            self.say(f"back toward the fight spot ({self.offset.round().tolist()} off)")
            self.hop(*v)
        else:
            self.hop(0, -210)

    def clear_minions(self, limit: float = 15) -> None:
        """Blizzard what's still standing around before hopping onto her body (2026-11-23 01:23: killed, then a chicken
        6 s later at the body among her Dark Ones)."""
        bot, sk = self.bot, self.sk
        t0 = time.time()
        near: tuple[int, int] | None = None
        try:
            while time.time() - t0 < limit:
                bot.check()
                if (bot.hp or 100) < RETREAT_HP:  # standing still among them to wait for potions was the chicken
                    if near:                      # (06:32: hopped off her body into a Dark One pack, 100 -> 49 %)
                        self.away_from(*near)
                        near = None
                    bot.sleep(0.5)
                    continue
                hit = self.find()
                if hit is None:
                    return
                (x, y), _, _ = hit
                near = (x, y)
                if iso_dist(x, y) < 220 and time.time() - self.backed_at > 1.5:  # in its reach: one hop off first
                    self.backed_at = time.time()
                    self.away_from(x, y)
                    continue
                if time.time() - self.blizz_at >= BLIZZARD_CD:
                    bot.press(sk["blizzard"])
                    self.blizz_at = time.time()
                else:
                    bot.press(sk["glacial_spike"])
                bot.click(x, y, "right", hover=0)
                bot.sleep(0.4)
        finally:
            bot.press(sk["teleport"])
            bot.input.move(1270, 590)

    def loot(self) -> list[str]:
        """Hop to where she was last seen and pick up what dropped."""
        from .lk import loot

        bot = self.bot
        if self.last:  # out of reach of her death burst first (04:21, 04:26: killed at 74 / 100 %, chicken 2-7 s later)
            self.away_from(*self.last)
            # she (her body) is now a hop further off along the same line
            v = np.array([self.last[0] - CENTER[0], self.last[1] - CENTER[1]], float)
            v = v / (float(np.hypot(*v)) or 1.0) * 380 * 1.17
            self.last = (int(np.clip(self.last[0] + v[0], 40, 1240)), int(np.clip(self.last[1] + v[1] * 0.6, 60, 560)))
        bot.sleep(4.5)  # the drop comes at the end of her death animation: fire + poison burst round her body for a
        # few seconds (2026-11-23 00:24 loot frame at 2.5 s: still exploding, Blizzaga poisoned at the body, no labels).
        # Wait it out at fighting range, then hop in
        self.clear_minions()
        if self.last:
            x, y = self.last
            dx, dy = x - CENTER[0], y + 40 - CENTER[1]
            if math.hypot(dx, dy) > 120:
                bot.press(self.sk["teleport"])
                dx, dy = in_play(dx, dy)
                bot.click(int(CENTER[0] + dx), int(CENTER[1] + dy), "right", hover=0)
                bot.sleep(TP_SETTLE + frame_lag(bot) + 0.4)
        from .lk import ensure_labels_on

        bot.input.move(1270, 590)
        ensure_labels_on(bot)
        bot.sleep(0.3)
        try:  # what was on the ground, for review (the filter hides most of her drop)
            import cv2

            from .config import ROOT

            d = ROOT / "logs" / "andy" / "loot"
            d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{time.strftime('%m%d-%H%M%S')}.jpg"), cv2.resize(bot.capture.grab(), None, fx=0.5, fy=0.5))
        except OSError:
            pass
        picked = loot(bot, take_all=True)
        bot.sleep(0.8)
        picked += loot(bot, take_all=True)  # a second look: labels under the first pick, late drops
        self.say(f"loot: {picked}")
        return picked


MINION_STREAK = 6      # finds in a row that aren't her ...
HER_LOST_S = 20.0      # ... with her unseen this long: go look for her (toward_throne)
ANTIDOTE_EVERY = 30.0  # s: an antidote's poison resist lasts about this long
ANTIDOTE_ROUNDS = 2    # at the stairs, then once more while she's still fighting


def antidotes(bot, why: str) -> int:
    """An antidote for her (belt key) and one for the merc (shift + belt key) against Andariel's poison
    (Stephen 2026-11-23). Returns how many were drunk."""
    from .vision.orbs import belt_kinds

    n = 0
    for merc in (False, True):
        kinds = belt_kinds(bot.capture.grab(), bot.cfg["vision"]["belt"])
        key = next((k for k, kind in zip(bot.cfg["hotkeys"]["potions"], kinds) if kind == "antidote"), None)
        if key is None:
            break
        if merc:
            bot.input.key_down("shift")
            bot.kill.sleep(0.05)
        bot.press(key)
        bot.kill.sleep(0.05)
        if merc:
            bot.input.key_up("shift")
        bot.kill.sleep(0.35)
        n += 1
    if n:
        log.info("antidote x%d (%s)", n, why)
    return n


def fight(bot) -> dict:
    """On Catacombs Level 4 at the stairs: go to her, kill her, loot. {"andy": 0/1, "picked": [...]}"""
    antidotes(bot, "at the stairs")
    hops(bot, ROUTE)
    f = AndyFight(bot)
    f.antidote_at, f.antidote_rounds = time.time(), 1
    dead = f.kill()
    log.info("Andariel %s (HP %.0f%% MP %.0f%%)", "dead" if dead else "NOT killed", bot.hp or 0, bot.mp or 0)
    if not dead:
        bot.save_failure("andy_not_killed")
        if f.last is not None and f.life < 0.6:  # hurt and then lost: she may have died out of sight. Look anyway
            return {"andy": 0, "picked": f.loot()}
        return {"andy": 0, "picked": []}
    return {"andy": 1, "picked": f.loot()}
