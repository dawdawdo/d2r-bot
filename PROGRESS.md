# Progress

**Current milestone:** Mephisto is a real task now (branch `tasks`): `python -m bot.run --mode chests --tasks meph`
(or lk,meph). Phase 1 (LK) done: M0–M6 met. Proposed bar for v1.0: 100+ runs untouched.

**2026-11-02 night (Stephen away):**
- Gem filter installed (D2R was at char select; closed it normally; old filter in `backups/filter-20261102-200736`).
- **Act 2 spawns fixed:** Lut Gholein view map (`maps/towns/a2/`, `bot/vision/viewmap.py`, `bot/townnav.py`). ORB
  offsets between her view and known views, scored by how many grid cells agree (palm trees/torches repeat all over
  town and faked a fix 1000 px away). Off the map she follows the old click walk until a view is recognised, then
  steers to the waypoint and clicks it (template when visible, else where the map puts it). 3/3 in
  `tools/town_map.py` + 1 live run (13 steps). `python tools/town_map.py --act 2` learns more views when needed.
- Meph belt: **`meph.buy_mana: false`** — the Materials rejuv stack is full (99) and spares were being dropped, so
  the belt restocks rejuvs from the stash instead of Ormus mana potions (they fix life and Mana Burn). Set it back
  to true if Stephen wants option C. Before: 4 runs, 1 kill, 2 chickens, 1 death, belts of mana with no life.
  After: 3 runs, 2 clean kills at 99-100 % (set + white picked), 1 chicken (hp 4, run 3).
- The memory reaper killed the batch at 21:58 (after run 3's chicken; she was at the menu). Batches are now 1 Meph
  run per command (a run can take 7 min; 3 blew the 10-min tool limit -> background -> reaped).
- **Belt restock bug fixed (452e313):** shift-click fills hidden rows of part-full columns, so the visible row lied:
  0-1 potions a restock and a false "stash out of rejuvs" flag. It now watches the stash stack: 16 filled live.
  Uses Full Rejuvs, then Rejuvs (both stacks on the Materials tab; Stephen: both fine to use and to save).
- Meph parks at the top centre (x 640-880) in many games and stays there at full life: now one lure hop along the
  bank (moved him 40 px: no help), then **new game after 8 parked rounds** instead of a 5-min timeout.
- Tally 22:51-23:24 (full belt): 1 kill (2 uniques + rune), 3 parked -> new game, 1 death (16 rejuvs gone in ~2 min:
  ES turns hits into mana loss), 2 fails (platform return, town after the death). Before it 21:48-21:58: 2 kills/3.
- Wake result doesn't predict where he parks (checked all of today's logs).
- **Next for Meph (needs Stephen's eye):** his other plan, merc tanks Meph on his own side while she casts Static
  x2 then Blizzard/Frozen Orb. The south bank tops out around 1/3 kills because of the parking.
- **Fell back to LK runs 23:25** (Stephen: "fall back to LK runs, because we know those work").

**2026-11-02 evening (Stephen at the PC; offline work only):**
- Gold: Stephen: spend what Meph needs. Inventory: Stephen will clean it up.
- Loot: no spare rejuvs for the stash any more (`loot.rejuv_spares: false`; belt slots only). Flawless + perfect
  gems: rule in `filters/LK Bot.fltr` + white labels that aren't key/rejuv/gold are picked as "gem" (gold now
  recognised by its "Gold" word). **Filter not installed yet: D2R was running.** `python tools/install_filter.py`
  with D2R closed (backs up the live copy first) — do this before the next bot session.
- Ormus: Botty's poses don't match Stephen's graphics (best < 0.65 with him on screen in 9 of 9 frames). The bot now
  saves his sprite (`fixtures/raw/ormus_crops/`) whenever the hover scan finds him -> build our own templates.
- LK 15:27-17:54: ~150 runs, 3 chickens, Ist rune. F12 by Stephen 17:54.

**Mephisto 2026-11-02 afternoon (Stephen watched, then away): south bank (his "bottom side of the moat").**
`meph.spot: south` (default; `dock` = the old way). Dock -> 2 hops to Stephen's view 206 -> buffs -> wake (hop onto
his platform, Static Field, search the whole screen for his name, one Blizzard if seen; every other try one hop
further up-left) -> back by view -> kill loop with hit-and-run volleys -> 14 s out of reach for his death throes ->
clear -> loot (take_all: every label color, so essences / ancients' statues get picked; no blue gear).
- **Where he stands decides it:** stuck at x 360-480 (left) = 8 kills at 97-99 % life; top centre (640-840, 20-70) =
  4 chickens/deaths in 5. Now: fight at x 280-600, wait elsewhere, never fight at 600-960.
- Waking is the slow part: some games he never shows in 7 wakes (5 min).
- Tally 13:44-15:26 (south): ~22 task runs, ~9 kills, ~5 chickens, ~4 deaths, rest timeouts/fails.
- **Stopped: Blizzaga is out of gold.** Deaths + merc revives (~50k each) used the 400k withdrawn today; her last
  death showed no gold toll. Ormus sold nothing (empty belt -> 2 deaths). A failed buy now asks for a withdrawal too.
- Loot: one real drop picked (unique); a Russet Armor + Mithril Coil didn't fit: **inventory has 2 free cells**.
- Other done today: Meph-only sessions type /players 1 once (no 7-then-1); Ormus sprite search (Botty's MIT poses,
  `bot/assets/templates/npc/`) before the hover scan, frames saved to tune it.

**Mephisto task (2026-11-01 evening, `bot/meph.py`, `bot/tasks/meph.py`, config `meph:`):** Ormus mana potions ->
WP Durance 2 -> learned path to Level 3 -> /players 1 -> 6 hops to the dock -> buffs -> Council hunt (name bars) ->
hop onto his platform to wake him -> back to the dock by the view -> Blizzard him across the moat -> dead = his
name over an empty bar -> clear -> one hop to his body -> loot. The run after a Meph game types /players 7 again.
- Results 21:20-22:35: ~10 kills in ~17 tries (set + unique drops picked). Failures: 3 deaths, ~4 chickens, 2 "pushed
  off the spot". Causes found and fixed one by one: he hits her from the dock when he stands at screen x >= ~400
  (now: wait one hop down the walkway), shield < 30% -> hop away and recover, a loot trip 2 hops into the unknown
  (now: only loot within one safe hop), the dock view's second match flipping the spot check (now: read twice),
  back_to refusing a right answer (min resp 0.10), a late chicken counted as a chicken not a death (now died).
- Bremm Sparkfist (Council, lightning enchanted + aura + extra fast) can reach the dock and burn her out: chicken.
- The merc dies most Meph runs (revive 50k from the shared stash; withdraw-on-empty works).
- **Tally 21:29-23:02: 32 task runs: 17 ok (16 kills), 4 chickens, 4 deaths, 8 fails** (2 early bugs; the rest
  mostly "pushed off the spot": back to the dock by view fails 3x). Stopped here per the 3-strikes rule and
  switched to LK batches until Stephen answers question 7.

**Charms (2026-10-31 17:10, Stephen):** filter rule "Show charms" (cm1–cm3, any rarity) installed with D2R
closed and kept by the game; blue (magic) labels are picked; the stowaway hovers each item and sends blue-named
ones (charms) to Blizzaga's personal tab. Tested live: a small charm Stephen had left in the inventory went to the
personal tab, a Hel to the Runes tab. 59-run batch 12:39–13:42 (F12 by Stephen). New long batch from 17:13.

**Merc + gold (2026-11-01):** overnight 23:08-08:51: 720 runs, 641 ok, 77 chickens, 2 deaths: the merc died at
21:55 and a failed revive disabled revives for the session (Blizzaga carried ~0 gold, her stash ~18k, revive 50k;
Stephen keeps gold in the shared stash, ~8.8M). Now: failed revive -> retry every 10 runs (max 3 in a row); "not
enough gold" -> withdraw 200k from the shared stash at the next stash stop, then revive. Live: withdraw + revive ok.
Runes 18:46-08:51 (~1020 runs): Sur x2, Ohm, Gul x2, Ist, Mal, Um, Pul. Rejuv spares ran out overnight (picks 272
vs drinks 258 without the merc). Shared stash has 5 pages (overflow could use them).

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

**Meph 2026-11-01 (Stephen: /players 1, 2nd recording):** dock reached, moat crossing by view works, name bar
reads Mephisto's life. Wyand blocked the dock (4/4); Stephen picked C. Now: mana potions bought at Ormus, merc revived, his safe
spot reached by view, Mephisto found and Blizzarded to 29% once, but his lightning reaches the spot and
waking him works 2 of 5. Details + next steps: docs/meph-navigation.md (2026-11-01 17:58-18:24).
**First bot kill 2026-11-01 18:54** (1 of 5 full tries; the rest chickened to his lightning bursts with him at
17-55%). Still a probe (`tools/probe_level3.py`), not yet a task in bot.run.
**19:30 best fight: classic dock moat trick** (Council hunted first, potions, merc): Meph 100->22% with her at
97-100% life; ended on a retreat-hop bug (fixed, untested). Next exact step in docs/meph-navigation.md (end).

**Next step (exact):** Stephen's decisions below. Until then: LK batches (proven, refill the belt from chests).
2026-10-30 23:08 - 10-31 09:50 (ended by Stephen's F12; Stephen away, foreground 8-min batches): LK 772/780 ok (7 chickens, 1 cut by my command timeout), ~47 s.
Stashed Pul x2, **Gul x2**, Ist, **Mal x2**, **Vex**, **Ohm**.
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

**Settings-proof (2026-10-31 noon, `bot/gamesettings.py`):** Stephen played and changed automap (Mini Map Right,
AUTO opacity), the filter (his "Looting"), /players 3, and ended in Act 1. Each session the bot now: sets automap
Full Screen + Center via Options (click, Apply, re-read Settings.json: the arrows wrap and Center only exists
with Full Screen); selects the "LK Bot" filter via Esc -> Loot Filter (checks lootfilter.json); types /players
only if Settings "Offline Difficulty Scaling" differs, and only after it sees the chat input line (keys typed
without it are hotkeys); an Act 1 spawn walks to the A1 WP -> Kurast Docks -> new game. All tested live.
Note for Stephen: after bot sessions his filter is "LK Bot" and automap Full Screen; switch back by hand.

**Meph 2026-10-30 late:** Stephen: potions may be bought for Meph; loot by filter; he used merc-tank then
moat trick (no Council clearing). AutoMapFade flipped to 2 (probably the bot's /players chat typed as
hotkeys) -> reset to Center via Options. One moat-trick try chickened (return hops didn't cross back).
Next: teach-and-repeat on his recorded views; make chat() verify the chat box. Details: docs/meph-navigation.md.

**Queued after Meph works (Stephen 2026-11-01):** spawn-act detection + WP to Act 3 for **Act 2 and Act 5**
(like `leave_act1`). Today only A1/A3/A4 are known; an A2 spawn ran the A3 walk and failed twice (17:13).

**Open questions for Stephen (Mephisto):**
(2. /players for Meph: 1, Stephen 2026-11-01; config `game.meph_players`.)
(3. Potions for Meph: answered 2026-10-30, buying is OK for Meph runs.)
(5. Meph vs Wyand: C chosen 2026-11-01, built.)
4. Live test windows for Meph (bot needs the PC; nothing live while Stephen uses it).
7. **Meph from the dock is ~55 % kills, ~1 death in 8.** Deaths: Council walking onto the dock, his lightning
   when he stands at screen x >= 400, a loot trip. Options: (a) I keep tuning live (more deaths, 28k gold + a merc
   revive each); (b) you watch 3-4 runs and tell me where she should stand (your own fights found a better spot
   by jumping around); (c) park Meph and only farm LK. LK batches run meanwhile.
(8. Gold: answered 2026-11-02, spend what's needed.) Old text: **Gold for Meph practice.** Each south-bank death costs her gold + a 50k merc revive; today ~400k from the shared
   stash. How much may Meph tuning spend (e.g. 1M a day), or should the merc stay dead for Meph (he's only Insight)?
(9. Inventory: Stephen will clean it up, 2026-11-02.) Old text: **Inventory space:** 2 free cells after stashing. Meph gear (armor 2x3) can't be picked. Can you clear some of
   Blizzaga's inventory, or should the bot only pick small items at Meph?
10. Act 2 town walk: you'd like it to go straight to the WP (as A3/A4 do). Next on my list after Meph.
(6. A2/A5 spawns: done 2026-11-02. Detected by template (a2_spawn / a5_spawn), walk to the town waypoint, back to
   Act 3. Live: A2 ok (85 s run), A5 ok (67 s run). Stephen will watch Meph runs for question 7.)

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
