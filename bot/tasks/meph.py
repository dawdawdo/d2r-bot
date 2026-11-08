"""Mephisto (Hell, Durance of Hate Level 3): (mana potions at Ormus) -> waypoint Durance 2 -> the
learned path to the Level 3 stairs (bot/durance.py, found by tools/find_durance.py) -> /players for
Meph -> the dock -> Council hunt, wake, moat-trick kill (bot/meph.py) -> loot -> save & exit.

Not ready until the stairs are found: maps/<route>/durance2_auto/graph.json.
"""
from __future__ import annotations

import json
import logging

from ..config import ROOT
from ..controller import BotError, Controller
from ..town import act4_to, cast_warcries, town_to_wp
from . import Task

log = logging.getLogger(__name__)


def route_file(cfg: dict):
    return ROOT / "maps" / cfg["game"]["route"] / "durance2_auto" / "graph.json"


def buying_mana(cfg: dict) -> bool:
    """Ormus mana potions before the fight: always (`buy_mana`), or while the stash is out of rejuvs."""
    from .. import state

    m = cfg.get("meph", {})
    return bool(m.get("buy_mana") or (m.get("buy_mana_when_dry") and state.load().get("stash_rejuvs_empty")))


class Mephisto(Task):
    name = "meph"
    act = 3
    enter_wp = "wp_durance_2"

    def __init__(self, cfg: dict) -> None:
        super().__init__(cfg)
        f = route_file(cfg)
        self.route = json.loads(f.read_text()) if f.exists() else None
        self.mcfg = cfg.get("meph", {})

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        return route_file(cfg).exists()

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        from ..lifecycle import create_game, save_and_exit
        from ..town import belt_ready, buy_mana_at_ormus, restart_in_act3

        if not chained:
            for attempt in range(2):  # Ormus wanders; the open-loop walk misses him now and then
                if not buying_mana(self.cfg) or belt_ready(bot):
                    break
                if getattr(bot, "act", 3) == 4:
                    restart_in_act3(bot)
                if not buy_mana_at_ormus(bot):
                    log.warning("Ormus: belt not filled (attempt %d)", attempt + 1)
                    from .. import state

                    # no gold on her: deaths took it all (2026-11-02 15:20: 4 empty belts, then 2 deaths)
                    state.save({**state.load(), "gold_needed": True})
                save_and_exit(bot)  # the town walk starts at the spawn
                create_game(bot, self.cfg["game"]["difficulty"])
                bot.wait_for("in_game", 10)
                bot.act = 3
            if getattr(bot, "act", 3) == 4:
                act4_to(bot, self.enter_wp, area=None)
            else:
                town_to_wp(bot, self.enter_wp, None, stow=stow)
        bot.wait_still(timeout=3)

    def farm(self, bot: Controller) -> dict:
        from ..durance import AutomapOdometer, StopGraph, ensure_automap, level_now, to_level3
        from ..meph import (SOUTH_EXTRA_WAKE, SOUTH_LURE, SOUTH_NEVER_X, SOUTH_RETREAT, SOUTH_SAFE_X, SOUTH_WAKE, WAKE_HOPS, MephFight, fight_from_dock,
                            fight_from_south, loot_meph, to_dock)
        from ..town import set_players

        if self.route is None:
            raise BotError("no Durance 2 route yet (tools/find_durance.py)")
        bot.deadline = bot.clock() + self.mcfg.get("timeout_s", 300)
        cast_warcries(bot)  # for the walk through Durance 2; again at the fight spot
        n = self.cfg["game"].get("meph_players")
        if n and getattr(bot, "players_now", None) != n and set_players(bot, n):
            bot.players_now = n  # the run loop sets LK's back next game
            # and the next session too: "players already set for this D2R window" was left standing, so every
            # LK run from 2026-11-01 23:03 to 11-02 06:36 (~540) ran at /players 1 (1 rune vs ~5 per 700 before)
            from .. import state

            st = state.load()
            st.pop("players_window", None)
            state.save(st)
        bot.sleep(1.0)
        auto2 = ROOT / "maps" / self.cfg["game"]["route"] / "durance2_auto"
        odo = AutomapOdometer.load(auto2, ensure_automap(bot))
        to_level3(bot, odo, StopGraph.load(auto2 / "graph.json"), None, auto2)
        bot.sleep(1.0)
        if level_now(bot) != 3:
            raise BotError("not on Durance of Hate Level 3")
        safety = self.cfg["safety"]
        saved = dict(safety)
        safety.update(self.mcfg.get("safety", {}))
        try:
            to_dock(bot)
            import time

            out = ROOT / "maps" / self.cfg["game"]["route"] / "durance3_auto" / "runs" / time.strftime("%m%d-%H%M%S")
            out.mkdir(parents=True, exist_ok=True)  # dock / dead / loot frames, for review
            if self.mcfg.get("spot", "south") == "south":
                fight = MephFight(bot, out=out, retreat=SOUTH_RETREAT, safe_x=SOUTH_SAFE_X, wake_hop=SOUTH_WAKE,
                                  extra_wake=SOUTH_EXTRA_WAKE, never_x=SOUTH_NEVER_X, lure=SOUTH_LURE,
                                  fight_parked=self.mcfg.get("fight_parked", False))
                dead = fight_from_south(fight)
            else:  # the dock (north-east bank): Council hunt first
                fight = MephFight(bot, out=out, wake_hop=WAKE_HOPS)
                dead = fight_from_dock(fight)
            log.info("Mephisto %s (HP %.0f%% MP %.0f%%)", "dead" if dead else "NOT killed", bot.hp or 0, bot.mp or 0)
            if dead:
                safety.update(self.mcfg.get("after_kill", {}))
            picked = loot_meph(fight) if dead else []
        finally:
            safety.clear()
            safety.update(saved)
        return {"picked": picked, "meph": int(dead)}
