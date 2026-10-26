"""Time the phases of live runs: wraps bot functions with timers, then runs bot.run's main.

  python tools/profile_run.py --runs 2 --mode chests

Prints total seconds and call counts per function at the end (nested times overlap).
"""
from __future__ import annotations

import functools
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import controller, lifecycle, lk, nav, run, town  # noqa: E402

TOTAL: dict[str, float] = defaultdict(float)
COUNT: dict[str, int] = defaultdict(int)


def _wrap(mod, name: str, label: str) -> None:
    fn = getattr(mod, name)

    @functools.wraps(fn)
    def timed(*a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            TOTAL[label] += time.perf_counter() - t0
            COUNT[label] += 1

    setattr(mod, name, timed)
    for other in (run, lk, town, lifecycle):  # names imported with "from x import y"
        if other is not mod and getattr(other, name, None) is fn:
            setattr(other, name, timed)


PHASES = [
    (lifecycle, "ensure_main_menu"), (lifecycle, "create_game"), (lifecycle, "save_and_exit"),
    (town, "set_players"), (town, "recover_corpse"), (town, "merc_alive"), (town, "needs_heal"),
    (town, "cast_buffs"), (town, "walk_route"), (town, "restock_belt"), (town, "open_town_wp"),
    (town, "check_area"), (town, "town_to_lower_kurast"),
    (lk, "check_fingerprint"), (lk, "open_chest"), (lk, "loot"), (lk, "run_route"),
    (nav, "hop"), (nav, "teleport_to"), (nav, "reanchor"), (nav, "anchor_bonfire"),
]


def main() -> int:
    for mod, name in PHASES:
        _wrap(mod, name, f"{mod.__name__.split('.')[-1]}.{name}")
    _wrap(controller.Controller, "wait_still", "Controller.wait_still")
    _wrap(controller.Controller, "wait_for", "Controller.wait_for")
    try:
        return run.main()
    finally:
        print(f"\n{'phase':36s} {'total s':>8s} {'calls':>6s} {'avg s':>6s}")
        for k in sorted(TOTAL, key=TOTAL.get, reverse=True):
            print(f"{k:36s} {TOTAL[k]:8.1f} {COUNT[k]:6d} {TOTAL[k] / COUNT[k]:6.2f}")


if __name__ == "__main__":
    raise SystemExit(main())
