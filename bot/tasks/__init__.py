"""Farming tasks. A task is what happens between "in a fresh Hell game, in town" and "save & exit":
get from town to the farming area (`enter`), then farm it (`farm`). Everything around that is
shared by all tasks: game lifecycle, safety (chicken, potions, flee), upkeep (repairs, keys, merc,
stowaway), logging (runs.csv, loot.csv).

  python -m bot.run --task lk --runs 20

Adding a task: a module here with a Task subclass, registered in TASKS.
"""
from __future__ import annotations

from ..controller import Controller


class Task:
    name = "task"
    act = 3  # the act new games start in; town routes assume it

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg

    def enter(self, bot: Controller, stow: bool = False) -> None:
        """From the new-game spawn in town to the farming area (stash stop on the way: stowaway)."""
        raise NotImplementedError

    def farm(self, bot: Controller) -> dict:
        """Farm the area; return stats ({"chests": n, "picked": [...], ...}). Exceptions from the
        safety layer (Chicken, Died, RunTimeout) propagate; the caller saves & exits."""
        raise NotImplementedError


def get_task(name: str, cfg: dict) -> Task:
    from .lk import LowerKurast

    tasks = {LowerKurast.name: LowerKurast}
    if name not in tasks:
        raise SystemExit(f"unknown task {name!r}; known: {', '.join(sorted(tasks))}")
    return tasks[name](cfg)
