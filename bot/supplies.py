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


def new_session() -> None:
    st = state.load()
    state.save({k: v for k, v in st.items() if k not in ("stash_rejuvs_empty", "refill_left", "restock_zero")})


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
    if not want or not st.get("stash_rejuvs_empty"):
        return False
    if "refill_left" not in st:
        state.save({**st, "refill_left": want})
        log.warning("stash out of rejuvs: LK until %d more are stashed", want)
    return True


def tasks_for_run(tasks: list, refill_tasks: list, cfg: dict) -> list:
    """`refill_tasks` is empty when the session has no boss to protect, or LK isn't ready."""
    return refill_tasks if refill_tasks and refilling(cfg) else tasks


def players_for(tasks: list, cfg: dict) -> int | None:
    """A Meph-only game plays at Meph's /players from the start (Stephen 2026-11-02: 7 then 1 wastes time)."""
    game = cfg["game"]
    if tasks and all(t.name == "meph" for t in tasks):
        return game.get("meph_players") or game.get("players")
    return game.get("players")
