---
name: project-goal-portable-app
description: "End goal is a portable Python application that runs on both Windows and Linux; plus inventory/stash policies (keys = 12, runes go to the shared Materials stash)"
metadata:
  node_type: memory
  type: project
  originSessionId: 4505bf4f-0217-4c27-b5fa-f04a1901ad81
  modified: 2026-10-25T23:47:13.196Z
---

- The final deliverable is a **portable application, preferably Python, runnable on Windows or Linux** (stated 2026-10-25). Keep all platform code behind `bot/io/` and avoid Windows-only dependencies elsewhere; a Linux backend is required eventually (see [[machines-and-target]]).
- Inventory policy: once keys are collected from chests, keep **exactly 12 keys (one stack / one inventory cell)**.
- **Runes go into the shared stash Materials tab** (the same tab holding the 99 Full Rejuvs). Long term, keys and rejuvs should come from chest loot rather than vendor/stash.

**Why:** Stephen's stated requirements, 2026-10-25.
**How to apply:** design new features (packaging, config, deposit logic) with cross-platform use in mind; implement the rune deposit at the existing stash stop in the town route. Related: [[loot-and-map-goals]].
