# Progress

**Current milestone:** M6 speed + soak. M1–M5 done. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-26 afternoon):**
- `python -m bot.run --runs N --mode chests`: launch/recover → Hell game → `/players 7` once per session →
  corpse pickup → (Ormus heal / Hratli repair + keys / **Asheara merc revive** when needed, then a fresh game)
  → buffs → town route → belt restock from stash → WP → LK → teleport route (odometry + bonfire re-anchor)
  → open chests → loot rune/unique labels → save & exit. Logs `runs.csv`.
- **Speed:** best runs now 54–63 s, 6 chests (were ~66–110 s). Town part ~21 s (was 27), LK part ~25–30 s (was 37–52).
  Teleport settle 0.45 → 0.2 s (0.15 still 10/10, 0.1 only 6/10), hops up to 420 px (520 loses tracking),
  no hover on teleport clicks, WP arrival detected by view change (was a 5 s loading-screen timeout every run),
  tighter walk-leg settle, shorter buff waits. `tools/profile_run.py` times every phase; `tools/tp_rate.py` measures teleports.
- Merc (Waheed) revived 2026-10-26 (50k gold). `town.merc_alive` = portrait template top-left; revive is automatic.
- Game window refocuses itself when a popup steals focus (AttachThreadInput trick).
- Guardian: potion at HP < 70% or MP < 25%, chicken at HP < 50% or ES broken (MP < 8% and HP < 75%), death, run timeout.

**Fixed 2026-10-26 evening (last 12 runs: 6,6,6,4,6,6,6,6 chests on the ok runs; best 53 s):**
- Desktop right-click: blocked-teleport detours rotated hops off the window bottom -> desktop menu stole
  focus every run. Rotated hops re-limited; `Controller.click` clamps to the client; focus thief is logged.
- "Entering Lower Kurast" banner pinned odometry at zero on the first hops: soft mask over static overlays.
- Lost odometry: spiral bonfire search (`nav.search_bonfire`) instead of skipping the rest; no blind 30 s
  chest scan while lost; long legs (camp to camp) count toward re-anchoring. Lost hops save a frame pair.
- Every "unique" pick ever was gold coins between labels. Labels now need 13 px text height. Real loot so far:
  a Hel rune (18:15). Pick frames are saved clean with the box in the file name.

**Broken / risks:**
- **Stash is out of rejuvs completely** (belt restock = 0). Chickens will rise until chest pickup of rejuvs exists.
- Chickens ~1 in 4-6 runs (ES broken at the camps).
- Occasional silent odometry error (no "lost" flag), fixed at the next bonfire anchor; costs that one chest.
- 1 fail "town waypoint not visible at end of route" in the last 15.

**Next step:**
1. Chest pickup of rejuvs (belt is empty) + keys: white labels; widths measured live: "Key" 37 px,
   "Rejuvenation" 133 px, "Potion" 68 px, "Gold" 51 px, gold amounts 32-49 px. Merc name "Waheed" 51 px
   (top-left: ignore). Templates better than widths.
2. More speed: `open_chest` ~1.5-2.8 s per chest (hover-scan rings), town walk 12.5 s (7 legs).
3. Soak (foreground, 3 runs per command; see memory note on the reaper).

**Open questions for Stephen:** none right now.

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`.
