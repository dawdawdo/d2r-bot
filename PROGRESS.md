# Progress

**Current milestone:** Mephisto (branch `tasks`): WP -> Level 3 works; the kill needs Stephen (questions below). Phase 1 (LK) done: M0–M6 met. Proposed bar for v1.0: 100+ runs untouched. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

**Works (live, 2026-10-27 ~05:10):**
- `python -m bot.run --runs 20 --max-minutes 8 --mode chests` (conda env d2r): launch/recover → Hell game (Hell
  button checked before clicking) → `/players 7` once per D2R window → buffs → chained town walk (9.1 s) → stash
  stop: stowaway → WP → LK → 6 chests → loot → save & exit. `runs.csv`, `logs/loot.csv`, `logs/loot/`.
  `tools/batch_summary.py "<since>"` prints one line per batch. `--max-minutes` ends a batch at the menu.
- **Stats 22:40 (10-26) – 08:10 (10-27):** 622 runs, 602 ok, 3361 chests, avg 47 s incl. repairs (clean ~44 s).
  Last 219 runs: 214 ok. Stashed (`logs/loot.csv`, tracked in git): Dol ×11, Hel ×10, Lum ×5, Io ×2, Ko, Fal,
  Lem, Mal, **Gul**, **Vex**, **Ohm**. No real unique ring yet (3 false "uniques" fixed in the label filter).
- **Upkeep without OCR** ("X of Y" compared as pictures, `vision/durability.py`): every 10 runs hover each equipped
  item; first wear seen → repair 20 runs later (backstop 60). Live wear in ~20 runs: Shako 11/12, Viper 23/24,
  boots 13/14, gloves 15/18. Keys: count the stack (`key_count`: 12/11/10/"3-9"/2/1) before buying; buy only < 3.
- **Danger handling:** ES broken → drink; still broken and life ≥ 60% → flee to the next camp (lose 3 chests, not 6);
  life < 50% → chicken. Chest hidden by a pack → short scan, 3 Frozen Orbs, rescan. A view jump (teleport when
  struck) stops the scan; the bot re-anchors, teleports back and scans once more.
- **Map learning** (`bot/learn.py`, `tools/learn_map.py`, `bot.run --relearn`): see roadmap; tested live.

**Act 4 shortcut (2026-10-27 evening, Stephen's idea; docs/roadmap.md):** clean runs end LK WP -> Pandemonium
  Fortress, so the next game spawns 1.6 s from a WP. ~46 live runs since: median 44.6 -> 42.9 s (runs that start
  in A4 but end in LK: ~37 s). Upkeep/stash runs go back through Act 3 automatically. Off switch
  `game.act4_exit: false`. The difficulty screen is now detected by the opaque Hell button (the title is
  see-through over the A4 menu art). **Filter check done:** runs picked and stashed Dol, Fal and other runes.
  Incident check: A4 starts 8 in 140 runs (5 of them clustered 20:50–21:15), A3 starts 0 in 58 (`--no-act4`
  A/B). No mechanism found (buffs cast, HP/MP 100% on arrival, merc alive). Keep watching `spawn: act` lines.
- **Filter raised to Pul+ runes** (Stephen, 22:20): installed with D2R closed, seen loaded in game.

**Broken / risks:**
- Chickens ~1 in 50 now. Teleport-when-struck jumps still cost a chest now and then.
- If Stephen rearranges his inventory, update `inventory.protected` (else his items get stashed).
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**
- Map hunting (reroll = play another difficulty, then Hell) is NOT built: it destroys the current map. Needs Stephen.

**Web page (branch `tasks`, 2026-10-27):** `bot_page.bat` or `python -m bot.web` -> http://127.0.0.1:8765
(password in `logs/web_password.txt`). Task checkboxes (LK ready, Mephisto "coming"), runs, time limit,
Start / Stop after this run / Stop now, session stats, loot, recent runs. The bot runs as its own process;
they talk via `logs/control.txt` + `logs/status.json` (bot/control.py). Phone access: set `web.host: 0.0.0.0`
(Windows firewall prompt once). Not yet used live.

**Mephisto (started 2026-10-27 22:30, v1.0 tagged before):** see docs/meph-navigation.md. Stephen chose
**option 2 (bot searches alone)** on 2026-10-28. LK + Meph run in one game, each toggled (branch `tasks`).
- `tools/find_durance.py --games 3 --hops 150` (resumes from `maps/blizzaga_hell/durance2_auto/`). Automap
  odometry holds (fix resp 1.00 at every arrival, no "fix lost" since the canvas fixes).
- Fixed 2026-10-28 evening: firelight/lit floors polluted the canvas (blob filter); canvas = hits / views since
  first seen (a plain average hid newly revealed walls); `AM_CHAR` (640, 500) -> (640, 370) (frontier targets
  were ~1000 px too far south); scans stop when struck; heal at Ormus before exploring.
- 2026-10-29 night: **WP -> Level 3 works live** (10.3 s, every game the town walk worked). The stand
  spot is where Stephen's 2nd teleport hold started; one teleport toward his held cursor, hover (636, 251)
  for "To The Durance of Hate Level 3" (`find_label`: frame diff), click. Recorder samples while held.
- **Level 3 mapped roughly** (docs/meph-navigation.md, `tools/probe_level3.py`): 6 hops (-350, -60) = the
  dock at the moat; Mephisto's side is across (portal side). Moat trick holds him at the far edge, but at
  /players 7 his lightning + Council Mana Burn break ES in 3-5 s on the dock. 5 tries, all chickens.

**Next step (exact):** Stephen's decisions below. Until then: LK batches (proven, refill the belt from chests).
2026-10-30 16:39-17:45 (supervised, foreground 8-min batches): LK 84/85 ok (1 chicken at HP 24%), ~43 s typical.
Stashed **Sur** and **Gul**. Ended by Stephen's F12 in a fresh game (A4 town); D2R left open.
2026-10-29 23:44-23:54: LK 11/11 ok (~41 s). A 60-min background batch was killed by Claude Code's low-memory
reaper at 23:54 (after run 2, on the way back to town; D2R left running in town). Not restarted: needs Stephen's OK
(or start Claude Code with CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1).
Town walk: ~1 in 5 games tonight stalled at leg 1/5 near the temple stairs (NPC/merc in the gap) and
failed at leg 5 (WP 500 px off, not matched). Costs one game; worth a look. A blue portal-like object
by the temple steps (~(520, 90) when stuck) is NOT the WP (clicked: nothing).

**Meph kill recorded (2026-10-30 22:26):** Stephen played Level 3 -> kill -> red portal to A4, 104 s, 247 steps
(239 right, 8 left; 19 without an automap fix, mostly at the end) in `maps/blizzaga_hell/durance3_route/`
(route.json + canvas committed, views/ local only). The recorder's save & exit tripped the kill switch again
(it reset the raw input's mouse watch, not the guard's): fixed. Next: replay the route as the bot's Meph task.

**Open questions for Stephen (Mephisto):**
2. /players for Meph games (7 now: Meph + Council very tanky)?
3. Potions for Meph: belt is empty, policy is chest rejuvs only. OK to buy some for Meph runs?

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
