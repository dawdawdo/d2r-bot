# Progress

**Current milestone:** M6 speed + soak. M1–M5 done. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-26 late evening):**
- `python -m bot.run --runs N --mode chests` (conda env d2r: `~/miniconda3/envs/d2r/python.exe`): launch/recover →
  Hell game → `/players 7` once per session → corpse pickup → (Ormus heal / Hratli repair + keys / Asheara merc
  revive when needed) → buffs → town route → (stash restock, skipped once known empty) → route-end fix → WP → LK →
  teleport route (odometry + bonfire re-anchor + spiral search when lost) → open chests → loot → save & exit. `runs.csv`.
- **Speed:** best runs 49.8 s and 52.4 s with 6 chests. Session-start run ~135 s (repair/keys/players).
- **Supply pickup (new):** white labels classified by word template (`label_key.png`, `label_rejuv.png`,
  `vision.labels.white_word`). Keys picked while `keys_left` < 12, rejuvs while a belt slot is empty. Gold scores ≤ 0.41 vs 1.0.
  Since 20:06: 43 runs, 33 ok, 5 chickens, 187 chests, 35 keys, 14 rejuvs picked. keys_left = 12 (no buying needed).
- Town WP found with an NPC on the right brazier (`town.find_town_wp`: full / left-half / near `wp_typical` fallbacks).
- Route-end correction by phase correlation vs `town_route_end.png`; skipped when the WP is already visible.
- Odometry: masked Hann window over static overlays, mean-subtracted; weak peaks trusted when they match the hop
  (landing ≈ 1.17× click offset). A chest missing at its spot marks the position suspect → re-anchor.
- Learned chest spots: learned BEFORE the post-scan odometry update (bug fixed in be8f2dc; learned.json restored
  from c6785b8). `LEARN_MAX_OFF = 150`.

**Broken / risks:**
- Chickens ~1 in 9 runs (ES breaks at camps; belt mostly empty, stash has 0 rejuvs).
- Occasional silent odometry error — now caught by "chest missing → suspect", costs time not the run.
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**

**In the middle of:** nothing half-done. Last commit be8f2dc verified live (135.8 s/5, 52.4 s/6, 49.8 s/6). 85 tests pass.

**Next step (exact):**
1. Soak a few more batches (foreground, `--runs 3`) to confirm the learning fix: chest scans should stay ~1.5–2.8 s,
   no 8–10 s scans. Check `runs.csv` chests/run and chicken rate.
2. Speed: `lk.open_chest` hover-scan rings (~1.5–2.8 s/chest) — try learned spot first with a tighter ring;
   town walk 12.5 s (7 legs) — fewer/longer legs; session-start overhead.
3. Check `east_nw` learned spot (895,470 vs scouted 1047,495) — probably an artifact of the old learning bug.

**Open questions for Stephen:** none. (Optional: refill the stash with rejuvs to cut chickens.)

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
