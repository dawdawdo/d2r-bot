# Progress

**Current milestone:** M6 soak + stowaway. M1–M5 done. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-26 night):**
- `python -m bot.run --runs N --mode chests` (conda env d2r: `~/miniconda3/envs/d2r/python.exe`): launch/recover →
  Hell game → `/players 7` once per session → (corpse pickup only after a death) → (Ormus / Hratli every 10 runs,
  counter persisted in `logs/state.json` / Asheara) → buffs → town route → stash stop: belt restock (skipped, stash
  empty) + **stowaway** → WP → LK (arrival checked by map fingerprint) → 6 chests → loot → save & exit. `runs.csv`.
- **Speed:** clean runs 45–51 s (6 chests). Repair runs ~87 s.
- **Stowaway** (`town.stowaway`, after runs that picked anything but rejuvs, and at session start): inventory scan
  (`vision/inventory.py`: empty / key / other; Stephen's items are `inventory.protected` cells in config), Ctrl+click
  loot into the stash (runes auto-route to the Runes tab; rings to shared page 1), drop key stacks beyond one
  (Ctrl+click with only the inventory open). An extra stack ⇒ kept stack is full ⇒ `keys_left = 12`.
  Stashed runes are named by diffing the Runes tab → `logs/loot.csv`; tooltips saved to `logs/loot/`.
  Found so far: Hel ×2, **Ohm** (23:20).
- Keys are picked only while the estimate is < 8 (`town.keys_pick_below`): one pickup can be a whole stack.
- Batches tonight: 30 runs since 23:00, 28 ok, 1 chicken (mana drained at east camp), 1 run lost odometry (2 chests).

**Broken / risks:**
- Chickens ~1 in 10–20 (ES broken by mana burn at camps). Belt rejuvs only come from chests.
- Lost-odometry recovery sometimes can't find the west bonfire (search fails → camp skipped).
- If Stephen rearranges his inventory, update `inventory.protected` (else his items get stashed).
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**

**Next step (exact):**
1. Keep soaking (foreground, ~9 runs per command ≈ 8 min).
2. Speed: chained town walk (legs are consistent by odometry, see `town walk legs` log line) ~2.5 s/run.
3. Recovery: better relocalization when lost (e.g. match against a stitched LK map).
4. Long term (Stephen): map hunting — reroll Hell maps until a good super-chest layout, learn it, run it.

**Open questions for Stephen:** none.

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
