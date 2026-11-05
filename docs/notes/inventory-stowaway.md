---
name: inventory-stowaway
description: Key pickups can add several keys (overflow into a 2nd inventory cell); a stash "stowaway" phase must move runes + unique rings to the stash
metadata:
  type: project
---

Stephen, 2026-10-26 evening:
- Picking up a key drop can add **more than one key** (drops are stacks). Counting +1 per pickup is wrong and
  overflow past 12 spills into a second inventory cell, eventually filling the inventory. Read the real count
  (inventory key tooltip "Quantity") or stop picking keys when unsure.
- Needs a **stowaway phase**: runes and unique rings go into the stash (runes -> shared Materials tab, see
  [[project-goal-portable-app]]). Not urgent (rare drops) but must exist eventually; the stash is on the town route.
- Longer term: the sorc should search for a good Hell map herself when she has none (see [[loot-and-map-goals]]).

**Why:** unattended soaks will otherwise fill the inventory and stop looting.
**How to apply:** do the stowaway at the existing stash stop next to the A3 WP; fix key counting before long soaks.
