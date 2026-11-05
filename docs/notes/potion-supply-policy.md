---
name: potion-supply-policy
description: LK = chest-drop rejuvs only (no buying, 2026-10-26); Meph runs may buy potions (2026-10-30)
metadata:
  node_type: memory
  type: project
  originSessionId: ecfc8c7c-c519-4f6e-8f53-55ff1e77a426
  modified: 2026-11-02T23:52:56.298Z
---

On 2026-10-26 the shared stash's 98 Full Rejuvs ran out (an MP < 45% potion threshold burned them in hours).
Stephen chose "chest rejuvs only": no buying potions from vendors; pick up rejuvs that chests drop, and drink
less often (MP < 25%). He also said chickens should be fixed by making runs faster, not by more potions.

**Why:** he wants the bot self-sustaining from its own loot and prefers speed over tankiness.
**How to apply:** don't add potion buying without asking; prioritize LK run time and rejuv/key pickup from
chests. Related: [[stephen-autonomy-prefs]], [[loot-and-map-goals]].

**Update 2026-10-30:** for **Mephisto runs** Stephen OK'd buying potions from vendors. LK stays chest-rejuvs-only.

**Update 2026-11-02:** spare rejuvs to the stash are fine (`loot.rejuv_spares: true`). What Stephen objected to was
red/blue potions bought at Ormus ending up on shared stash page 1 (an overflow buy -> inventory -> stowaway).
