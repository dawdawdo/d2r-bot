---
name: phase1-done-bar
description: LK bot "done" = 100 runs in one untouched session (chickens OK, >=95% ok), then tag v1.0; Stephen wants more farming tasks after
metadata:
  type: project
---

Agreed with Stephen 2026-10-27: phase 1 (LK chests) counts as done after one unattended session of 100+ runs with
no code changes or restarts in between: no crashes/stuck/idle outside town, >= 95% ok, ~6 chests per ok run,
upkeep (stowaway, repairs, keys) working on its own. Chickens are passes. Then tag `v1.0`.

He has other farming tasks to add next. A task-plugin refactor (bot/tasks: Task.enter/farm, LK = first task)
sits on branch `tasks`, not yet run live; merge after a live check.

**Why:** Stephen asked "when is it done" and wants to reuse the bot for more farming.
**How to apply:** run the 100-run test only when he says the PC is free ([[stephen-autonomy-prefs]]); ask which
task is next before designing it. Related: [[loot-and-map-goals]].
