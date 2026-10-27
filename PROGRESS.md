# Progress

**Current milestone:** M6 soak; map learning built. M1–M5 done. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-27 ~01:20):**
- `python -m bot.run --runs N --mode chests` (conda env d2r: `~/miniconda3/envs/d2r/python.exe`): launch/recover →
  Hell game (Hell button checked before clicking: another difficulty regenerates the map) → `/players 7` once per
  D2R window → (corpse click only if the last run died; flag in `logs/state.json`) → (Ormus / Hratli every 10 chest
  runs / Asheara) → buffs → **chained town walk** (odometry, 9.1 s) → stash stop: stowaway → WP → LK → 6 chests →
  loot → save & exit. `runs.csv`, `logs/loot.csv` (stashed runes by name), `logs/loot/` (item tooltips).
- **Stats since 23:00:** 137 runs, 125 ok, 7 chickens (before the ES rescue), 542 chests. Clean runs avg 44 s.
  Last batch 11/11. Found: Hel ×3, Dol ×2, **Ohm**.
- **Stowaway** (`town.stowaway`): inventory scan (`vision/inventory.py`; Stephen's items = `inventory.protected`),
  Ctrl+click loot to the stash (runes auto-route to the Runes tab), drop key stacks beyond one; keys picked only
  while the estimate < 8.
- **Energy shield broken** → drink a belt potion first; chicken only if still broken / belt empty.
- **Map learning** (`bot/learn.py`, `tools/learn_map.py --name X --all --games 15`): explore LK from the WP over
  several games, bonfire sightings, verify camps by chest tooltips, shortest route (nw before nw_deep).
  `bot.run --relearn`: two fingerprint misses in a row → learn the new map and keep farming (route saved in
  `logs/state.json` key `route`; delete it to go back to config). Tested live with a forced mismatch: 2 games found
  and verified both camps.

**Broken / risks:**
- Chickens ~1 in 15 (mana burn at camps); the ES rescue costs belt potions.
- If Stephen rearranges his inventory, update `inventory.protected` (else his items get stashed).
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**
- Map hunting (reroll = play another difficulty, then Hell) is NOT built: it destroys the current map. Needs Stephen.

**Next step (exact):**
1. Keep soaking (foreground, ~11 runs per command ≈ 9 min).
2. Map hunting design: score a fresh map from a short exploration; only with Stephen's go-ahead.
3. Linux backend (later; GLaDOS not in scope yet).

**Open questions for Stephen:** none blocking. (Map hunting: when you want it, it will replace Blizzaga's map.)

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
