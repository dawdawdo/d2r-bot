"""Rejuv supply: when the stash runs dry, boss sessions farm LK until it's stocked again (Stephen 2026-11-05).

The night of 2026-11-04 Meph emptied the stash at 00:01 and fought 8 hours on an empty belt: 2 chickens in 43 runs
before, 40 + 4 deaths in 208 after. LK chests refill it (about 25 rejuv picks an hour, 2026-11-04).

logs/state.json: `stash_rejuvs_empty` stops restock trips; `refill_left` = rejuvs still to stash before bosses resume.
Both are cleared at session start, so rejuvs Stephen adds by hand count: the first restock checks again.
"""
from __future__ import annotations

import logging

from . import state

log = logging.getLogger(__name__)

ZERO_RESTOCKS = 2  # in a row, with a belt slot empty; one could be a misread belt


_TABLES = None


def gold_total(cfg: dict) -> int | None:
    """Her gold: carried + her own stash + the shared stash, read from the live save files (read only; the game writes
    them at each save & exit). None when a file is missing or doesn't parse (mid-write)."""
    global _TABLES
    from pathlib import Path

    from . import d2save
    from .armory import STASH

    try:
        _TABLES = _TABLES or d2save.tables()
        saves = Path(cfg["paths"]["save_dir"])
        d2s = d2save.read_d2s(saves / f"{cfg['game']['character']}.d2s", _TABLES)
        stats = {int(s["id"]): int(s.get("value") or 0) for s in d2s.get("stats") or []}
        shared = sum(int(tab.get("gold") or 0) for tab in d2save.read_d2i(saves / STASH, _TABLES))
        return stats.get(14, 0) + stats.get(15, 0) + shared  # 14 carried, 15 her stash
    except Exception as e:  # noqa: BLE001  an unreadable save must never stop a run
        log.info("gold unknown: %s", e)
        return None


def gold_block(st: dict, gold: int | None, cfg: dict) -> tuple[bool, dict]:
    """(LK this run?, state). Gold comes in blocks (Stephen 2026-11-24: "a good long run to LK, then a good long run to
    Andy"): a merc revive is ~50k and Andariel's merc dies about every 4th run, so switching back after one revive's
    worth of LK left her merc dead most of the time (LK chickens 62 % without him vs 20-30 %). The block starts when
    gold can't pay the next revive (or a revive just failed for gold, when the save can't be read) and ends at
    town.gold_block_until."""
    t = cfg["town"]
    need, until = t.get("merc_revive_gold", 50000), t.get("gold_block_until", 500000)
    block = bool(st.get("gold_block"))
    if not block:
        broke = gold < need if gold is not None else bool(st.get("stash_gold_empty"))
        return (True, {**st, "gold_block": True}) if broke else (False, st)
    if gold is not None and gold >= until:
        return False, {**st, "gold_block": False, "stash_gold_empty": False}
    return True, st


def new_session() -> None:
    """A new session looks at the stash again (Stephen may have added rejuvs), but a refill under way goes on to its
    end: "do LK runs until she stocks up again, then go back to Mephisto" (Stephen 2026-11-08; restarted sessions
    had gone back to Meph with 10 of 40 stashed). To end one early: delete refill_left from logs/state.json."""
    st = state.load()
    state.save({k: v for k, v in st.items() if k not in ("stash_rejuvs_empty", "restock_zero")})


def restocked(moved: int, slots_gone: bool) -> bool:
    """Record a restock's result. True the moment the stash is judged dry. `slots_gone`: both stacks read empty.
    A zero with potions still showing counts too: 199 of those on 2026-11-05 never set the old flag."""
    st = state.load()
    if moved > 0:
        st.pop("restock_zero", None)
        state.save({**st, "rejuv_stash_full": False})  # room in the stack again
        return False
    zeros = st.get("restock_zero", 0) + 1
    dry = slots_gone or zeros >= ZERO_RESTOCKS
    if dry:
        st.pop("restock_zero", None)
        st.update(stash_rejuvs_empty=True, rejuv_stash_full=False)  # a stale "full" would block spare pickups
    else:
        st["restock_zero"] = zeros
    state.save(st)
    return dry


def needs_a_page(left: list, rejuvs: set, stacks: set) -> list:
    """What's still in the inventory and needs a free stash cell. Rejuvs and other stacked items go to their stacks:
    one that stayed means that stack is full, not the stash, so it must not count towards a full stash."""
    return [cell for cell in left if cell not in rejuvs and cell not in stacks]


def after_stowing(st: dict, rejuvs: int, stack_full: bool) -> dict:
    """The state after the stowaway put `rejuvs` in the Materials stack."""
    st = dict(st)
    left = st.get("refill_left")
    if stack_full or (left is not None and left - rejuvs <= 0):
        st.pop("stash_rejuvs_empty", None)
        st.pop("refill_left", None)
        if left is not None:
            log.warning("rejuvs restocked: boss runs resume")
    elif left is not None:
        st["refill_left"] = left - rejuvs
        if rejuvs:
            log.info("rejuv refill: %d to go", st["refill_left"])
    elif rejuvs:
        st.pop("stash_rejuvs_empty", None)  # restocks can take from the stash again
    return st


def refilling(cfg: dict) -> bool:
    """Should this run farm rejuvs instead? Starts the count the first time it sees a dry stash."""
    want = cfg["town"].get("refill_rejuvs", 0)
    st = state.load()
    if not want or not (st.get("stash_rejuvs_empty") or "refill_left" in st):
        return False
    if "refill_left" not in st:
        state.save({**st, "refill_left": want})
        log.warning("stash out of rejuvs: LK until %d more are stashed", want)
    return True


def tasks_for_run(tasks: list, refill_tasks: list, cfg: dict) -> list:
    """`refill_tasks` is empty when the session has no boss to protect, or LK isn't ready."""
    if tasks and all(t.name == "meph" for t in tasks) and cfg.get("meph", {}).get("buy_mana_when_dry"):
        return tasks  # Meph buys at Ormus instead (bot/tasks/meph.py buying_mana)
    return refill_tasks if refill_tasks and refilling(cfg) else tasks


def saving_rejuvs(active: list, refill_tasks: list, cfg: dict) -> bool:
    """A refill run doesn't drink. A rejuv takes about 3.75 min of LK to replace and a chicken costs under a minute;
    LK drank about half of what it picked up (42 of 78, 2026-11-05/06)."""
    if refill_tasks:
        return active is refill_tasks and cfg["town"].get("refill_no_potions", True)
    # An LK-only session (features.save_rejuvs, Stephen 2026-11-20 "she used to get more rejuvs than she used"): with
    # the stash dry, no drinking until that many more are stashed. LK found ~4 per 100 chests and drank about twice that.
    n = cfg["town"].get("lk_save_rejuvs", 0)
    return bool(n) and bool(active) and all(t.name == "lk" for t in active) and \
        refilling({**cfg, "town": {**cfg["town"], "refill_rejuvs": n}})


def players_for(tasks: list, cfg: dict) -> int | None:
    """A Meph-only game plays at Meph's /players from the start (Stephen 2026-11-02: 7 then 1 wastes time)."""
    game = cfg["game"]
    if tasks and all(t.name == "meph" for t in tasks):
        return game.get("meph_players") or game.get("players")
    own = {cfg.get(t.name, {}).get("players") for t in tasks} if tasks else set()
    if len(own) == 1 and None not in own:
        # every task has the same /players (Andariel: 1): play at it from the start. 7 then 1 each game cost two chat
        # commands, and a failed one meant a fight at players 7 (2026-11-23 15:13: chat didn't open; 15:14 a miss)
        return own.pop()
    return game.get("players")
