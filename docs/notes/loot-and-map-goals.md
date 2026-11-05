---
name: loot-and-map-goals
description: "Stephen's loot wants (Dol+ runes, unique rings, optional cube gems) and long-term map-relearn / map-hunting goal"
metadata:
  node_type: memory
  type: project
  originSessionId: 4505bf4f-0217-4c27-b5fa-f04a1901ad81
  modified: 2026-11-01T00:27:45.810Z
---

- Loot: runes **Dol (r14)+**, unique rings (SoJ hope); gems for cubing Dol+ upward only if missing (he probably has them, so off by default).
- Later updates: runes raised to Pul+ (2026-10-27); charms -> Blizzaga's personal tab (2026-10-31). "Eligible for Chronicle" unique/set items that get past the filter: KEEP them, Stephen is building a holy grail (2026-10-31). Bot may fill personal + shared stash with charms/Chronicle items; Stephen clears them between sessions.
- Approach: D2R native loot filter `filters/LK Bot.fltr` hides everything else; bot picks visible labels.
- Stephen approved adding any `.fltr` loot filter files to the save folder as needed. This is the only exception to "never write in the save folder"; character saves are still off-limits, and back up first.
- The current Blizzaga Hell map will eventually be replaced by accident. He wants map-change detection plus relearning, and eventually a full "reroll maps until a good super-chest layout, learn it, then run" pipeline. One thing at a time; see docs/roadmap.md.
- Each LK bonfire has **three** super chests (Stephen, 2026-10-25).
- Blizzaga wears an item with teleport-when-struck: random jumps in fights. Handle in code (jump detection + landmark re-anchoring) rather than removing the item; removal is the fallback.
- He wants to authorize sessions remotely (Claude / email / text all OK) and wants the bot to launch D2R itself.

**Why:** stated 2026-10-25.
**How to apply:** keep routes as per-map data with a fingerprint; never hard-code the route. Related: [[stephen-autonomy-prefs]].

Update 2026-10-27: next target is **Dracul's Grasp** via Hell Mephisto runs (Stephen accepted the proposal; he
wants the quickest route, not the highest drop rate per se). Filter is now tight BiS-only: unique rings (SoJ for
Dclone), Dracul's, Arachnid Mesh, Andariel's Visage, unique amulets/jewels/grand charms, Tal Rasha's Lidless Eye,
Dol+ runes, keys/rejuvs. Odds and codes in docs/loot.md.
