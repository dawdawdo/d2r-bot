"""Farming tasks. A task is what happens between "in a fresh Hell game, in town" and "save & exit":
get from town to the farming area (`enter`), then farm it (`farm`). Everything around that is
shared by all tasks: game lifecycle, safety (chicken, potions, flee), upkeep (repairs, keys, merc,
stowaway), logging (runs.csv, loot.csv).

  python -m bot.run --mode chests --tasks lk,meph --runs 20

The tasks given run one after another in the SAME game, in catalog order (LK, then Mephisto): a task
that ends at a waypoint (LK) takes it straight to the next task's waypoint (`enter_wp`), so the next
one starts there (`enter(bot, chained=True)`). If the hand-off fails the rest of the game is skipped.
Each task is switched on or off on its own (web page checkboxes, or the --tasks list).

Adding a task: a module here with a Task subclass, registered in TASKS and CATALOG.
"""
from __future__ import annotations

from ..controller import Controller


class Task:
    name = "task"
    act = 3  # the act new games start in; town routes assume it
    enter_wp: str | None = None  # ui point on the Act III waypoint tab where the task starts, if it does

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.next: Task | None = None  # the task that follows in the same game (set by the run loop)

    def enter(self, bot: Controller, stow: bool = False, chained: bool = False) -> None:
        """From the new-game spawn in town to the farming area (stash stop on the way: stowaway).
        `chained`: the previous task already brought us to `enter_wp`."""
        raise NotImplementedError

    def farm(self, bot: Controller) -> dict:
        """Farm the area; return stats ({"chests": n, "picked": [...], ...}). Exceptions from the
        safety layer (Chicken, Died, RunTimeout) propagate; the caller saves & exits. When `self.next`
        is set and the task can, it ends at the next task's waypoint and sets stats["chained"] = True."""
        raise NotImplementedError

    @classmethod
    def ready(cls, cfg: dict) -> bool:
        """Can this task run now (e.g. its route has been learned)?"""
        return True


# What the web page lists, in run order. `ready` is filled in by catalog().
CATALOG = [
    {"name": "lk", "title": "Lower Kurast super chests",
     "about": "6 super chests at the two bonfire camps. Runes, gems, keys, rejuvs. About a minute a run."},
    {"name": "meph", "title": "Mephisto",
     "about": "Durance of Hate 3, south bank. Chronicle items, statues, essences. About 2 min a run."},
    {"name": "tunnels", "title": "Ancient Tunnels",
     "about": "Lost City trap door, area level 85: Archon Plates and other elite bases. About 5 min a run."},
]
ORDER = [t["name"] for t in CATALOG]


def _classes() -> dict:
    from .lk import LowerKurast
    from .meph import Mephisto
    from .tunnels import AncientTunnels

    return {c.name: c for c in (LowerKurast, Mephisto, AncientTunnels)}


def catalog(cfg: dict) -> list[dict]:
    classes = _classes()
    return [{**t, "ready": t["name"] in classes and classes[t["name"]].ready(cfg)} for t in CATALOG]


def get_task(name: str, cfg: dict) -> Task:
    tasks = _classes()
    if name not in tasks:
        raise SystemExit(f"unknown task {name!r}; known: {', '.join(sorted(tasks))}")
    return tasks[name](cfg)


def get_tasks(names: list[str], cfg: dict) -> list[Task]:
    """The tasks for one game, in run order, each linked to the next."""
    names = sorted(dict.fromkeys(names), key=lambda n: ORDER.index(n) if n in ORDER else len(ORDER))
    tasks = [get_task(n, cfg) for n in names]
    for a, b in zip(tasks, tasks[1:]):
        a.next = b
    return tasks
