# Progress

**Current milestone:** M6 soak; map learning built. M1–M5 done. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-27 ~03:45):**
- `python -m bot.run --runs 20 --max-minutes 8 --mode chests` (conda env d2r): launch/recover → Hell game (Hell
  button checked before clicking) → `/players 7` once per D2R window → buffs → chained town walk (9.1 s) → stash
  stop: stowaway → WP → LK → 6 chests → loot → save & exit. `runs.csv`, `logs/loot.csv`, `logs/loot/`.
  `tools/batch_summary.py "<since>"` prints one line per batch. `--max-minutes` ends a batch at the menu.
- **Stats 01:20–03:40:** 148 runs, 145 ok (3 chickens), 862 chests, avg 49.7 s incl. repairs (clean ~43 s).
  Found tonight: Hel ×5, Dol ×4, Lum ×2, Lem, **Ohm**, **Vex**.
- **Upkeep without OCR** ("X of Y" compared as pictures, `vision/durability.py`): every 10 runs hover each equipped
  item; first wear seen → repair 20 runs later (backstop 60). Live wear in ~20 runs: Shako 11/12, Viper 23/24,
  boots 13/14, gloves 15/18. Keys: count the stack (`key_count`: 12/11/10/"3-9"/2/1) before buying; buy only < 3.
- **Danger handling:** ES broken → drink; still broken and life ≥ 60% → flee to the next camp (lose 3 chests, not 6);
  life < 50% → chicken. Chest hidden by a pack → short scan, 3 Frozen Orbs, rescan. Scans stop on view jumps.
- **Map learning** (`bot/learn.py`, `tools/learn_map.py`, `bot.run --relearn`): see roadmap; tested live.

**Broken / risks:**
- Chickens ~1 in 50 now. Teleport-when-struck jumps still cost a chest now and then.
- If Stephen rearranges his inventory, update `inventory.protected` (else his items get stashed).
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**
- Map hunting (reroll = play another difficulty, then Hell) is NOT built: it destroys the current map. Needs Stephen.

**Next step (exact):**
1. Keep soaking (`--runs 20 --max-minutes 8`, foreground).
2. Map hunting design: score a fresh map from a short exploration; only with Stephen's go-ahead.

**Open questions for Stephen:** none blocking.

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
