# Progress

**Current milestone:** Mephisto is a real task now (branch `tasks`): `python -m bot.run --mode chests --tasks meph`
(or lk,meph). Phase 1 (LK) done: M0–M6 met. Proposed bar for v1.0: 100+ runs untouched.

**TODO (Stephen 2026-11-08 evening): web dashboard on his website.** "A hook that checks in to my website ... a
console/dashboard kind of like my armory page but on the web ... remotely start and stop the bot and choose what's
running without using Claude Code." GLaDOS side is DONE: `bot/supervisor.py` POSTs a status snapshot every 30 s
(`remote.url` + `remote.token_file` in config.local.yaml, off until set) and applies the reply's `desired`
(run/tasks/mode/max_fail_streak) or `command` (stop_now/stop_after_run). Outbound only. **Still needed from Stephen:**
which site + stack/hosting (convergentblue.com? static or with functions/Workers?), the armory page URL/code to match
its look, auth preference. Then build: the endpoint (store snapshot + desired), the dashboard page (status, runs/h,
kill rate, loot feed, start/stop, task picker). Also: make the local `bot/web` go through desired.json instead of
spawning bots; supervisor as a systemd --user unit for reboots (ask first: system setting).

**2026-11-09 12:20: after both machines restarted.** Syncthing test passed: Stephen's Singularity play (Blizzaga,
stash, filter) arrived complete, no conflicts. His filter edit ("Hide gems" off: redundant with the two gem show
rules, no change in what shows) is in the repo filter now. Supervisor restarted on GLaDOS (meph); it doesn't come
back after a reboot (systemd --user unit still waits on Stephen's OK). New, untested live:
- "Stash full" must hold on two stash visits in a row (different games) before a session stops.
- Chest misses (~5% of chest visits, nw chests ~8%): failure frames show the chest visible and closed 30-45 px off,
  between 35 px hover grid points; the retry used the same grid. Retry now scans a half-step-shifted grid, radius 105.
  Check: `chest hidden` lines followed by a find. Deeper fix if it isn't enough: learned positions are grid points
  that touched the chest edge, not its center.
- Web dashboard: convergentblue.com is static on Cloudflare (via GitHub); Workers is an option. Stephen is getting a
  handoff doc for the armory page.

**2026-11-09 07:20: supervisor ran 7 h untouched overnight (3 sessions).** Fixed: a stowaway rescan misread 13
cells and stopped a session on "stash full" with plenty of room (only pre-stash loot cells count now; a
`stowaway_spill` frame is saved if it happens again). Filter regenerated + installed from the Chronicle (254/112 ->
117 unique + 22 set codes; GLaDOS reads the tables from fixtures/chronicle via config.local.yaml). **Open:** the
chest sweep sometimes hovers right over a visible, closed chest and gets no tooltip (07:04 west_nw: chest 37 px from
expected, a pack beside it; 3 Glacial Spikes, 2nd sweep missed too). About 33 chests lost in ~174 LK runs this way.
Next: tooltip frames with D2R_DEBUG_TOOLTIPS to see what the hover shows.

**2026-11-08 16:35: GLaDOS Meph 10/10 kills (~151 s a run, no potions drunk, merc never died).** Fixed today
(Stephen away, asked: keep running Meph, make it better, fix the town WP, cube everything, frame-queue cap only if
material):
- Top Meph failure "couldn't get back from his platform" (also Windows): back_to's ~368 px-down hop clicked the HUD
  (y 698), 6 times. `nav.in_play()` shortens any hop to land in (20..1260, 20..630); used by meph/nav/lk hops.
- Town WP misses: the stash fallback click walked her behind the chest / onto the bridge. The chest beside her is
  matched at 0.6 (`_stash_beside_her`; GLaDOS chest reads 0.71 vs the Windows template); a WP click that doesn't
  move her walks halfway first (`unstick_toward`).
- `/players` never typed on GLaDOS (chat text smaller; chat detected by its icon now): Meph had run at players 7.
- Esc that meant "close a dialog" opened the game menu (Ormus/Asheara/stash): `close_dialog()`.
- Inventory toggles checked by the panel header (`inventory_open`): a lost one left it open over Durance 2.
- Meph loot: leaves his body as soon as life drops in the name sweep (HP 96 -> 5 there once).
- Fullscreen D2R (Stephen played): Alt+Enter before resizing (`Window.is_fullscreen`, X11 only; Windows says False).
- Cube plan respects 99-stacks (Stephen moved the stuck sapphire; cube everything). `meph.buy_mana_when_dry` (Ormus
  mana instead of LK refill) built but OFF: Stephen wants LK refill runs, then Meph (2026-11-08).
- Frame-queue cap: not done. The Proton cost left is ~0.08 s a teleport, ~2% of a run: held as a future option.
- Evening (Stephen's calls): never buy red/blue potions (belt ones drunk in town to make room for rejuvs); stash
  dry -> LK refill to 40, kept across session restarts; merc revive retried the next run (was 10 runs later), his
  Insight is her regen; cubing switches to the Runes tab first (Personal has no cube grid: nothing cubed all day,
  then 95 transmutes at 18:51); /players remembered with its value, not just the D2R window.
**Open:** GLaDOS stash is out of rejuvs (refill count 40); untested on Windows: everything above (compile/offline only).

**2026-11-08: GLaDOS (Linux) port works. Meph 9/10 kills (same as Windows).** Branch `tasks` on both machines
(CLAUDE.md). Details and all GLaDOS settings are in `docs/glados.md`. What it took, beyond the uinput/X11 backend:
the bot launches D2R via Steam -> Battle.net (`--exec="launch OSI"`) and clicks the Offline tab; D2R moved to the SSD
and swap added (loads 30 s-2 min -> 12 s); per-machine game settings (Settings.json isn't synced): Large Font Mode,
Brightness max, VSync off, Windowed 1280x720; capture 52 -> 17 ms a frame; Proton lag handled by `game.input_lag`
(0.05 s) and `game.frame_lag` (0.08 s on teleport settles); chest tooltip finder made robust (thick letters, near-black
shadows). LK: runs ok, about 56 s from the waypoint (upkeep games extra on a fresh `state.json`).
(Open items from this entry: all handled 16:35, above.)

**2026-11-07 12:50: cubing at the stash (Stephen's ask).** "Leave five of each lower gems and rune, cube up through maybe Fal; account for gems required for runes." `bot/cube.py` plans (pure, `tests/test_cube.py`): runes first, bottom up, El..Ko -> up to Fal (Thul+ take a chipped/flawed gem, `RUNE_GEM`); then gems up to `cube.top_grade` (Flawless; Perfect is one word away, **ask Stephen**); gems rune recipes take (`FOR_RUNES`) are never cubed up, since the filter no longer picks up chipped/flawed. `bot/vision/stack_count.py` reads the Gems and Runes tab counts (digit shapes from the Gems tab, normalized correlation; a rune's "1" is dim: tens 1 by contrast with the stone, trailing 1 by score 0.65+). Live-checked counts by moving 9 of a stack into the cube. `bot/cubing.py`: Ctrl+Shift+click a stack -> one into the stash's cube grid, Transmute (224, 500), Ctrl+Shift+click the result back; every `cube.every_hours` (6) from `town_to_wp`. ~4.8 s a transmute. `tools/stash_probe.py` for live stash pokes.
- Stephen answered (19:00): yes to both. `cube.top_grade: Perfect`; filter rule "Show lower gems" (21 chipped/flawed/normal codes) installed with D2R closed (backup `filter-20261107-190056`). Bot relaunched D2R; first Perfect pass planned 159 transmutes at 19:02. Watch: chipped stacks piling up (never cubed, kept for rune recipes); stash open needed 3 tries at 19:02.

**2026-11-07 09:10: Meph again, Stephen away all day.** Night on `safe`: 145 kills of 161 Meph runs (90%), 2 chickens, 0 deaths; refills 2.1 h then 1.4 h. Stopped at 08:16 on a false "stash full": a lit grid line in empty cell (3, 0) read as an item (`is_empty` now skips a 2 px rim; fixture `empty_cell_lit_edge_3_0.png`). Stephen changed gear: Arachnid Mesh for Goldwrap, Chance Guards for Magefist. Flawless Sapphire and Ruby stacks are full (dropped, as designed). Top Meph failure: couldn't get back from his platform (9 of 16).

**2026-11-06 22:40: `risk: safe` in config.yaml, Stephen's call.** One word flips `safe` / `fast` (`risk_levels`). Safe: area clear before looting, normal drinks after the kill, Meph chicken at 40% (my pick; was 25%), LK refill runs drink. Fast: the opposite, as tried today. Both keep the wider search, the single look at the drop, the drink on every chicken. **Check:** Meph kill rate and chickens at 40%; it was about 87% at 25%.

**2026-11-06 22:20: no deaths wanted.** Stephen wants to keep her experience. LK refill runs drink again (`town.refill_no_potions: false`), after a confirmed death in 90 no-drink runs (respawn frame `fixtures/failures/20261106-204930_*`). Every HP chicken now drinks on the way out. Max life is 201.

**2026-11-06 20:30: quicker Meph kills (Stephen OK'd).** `find_meph` searches 16 more points when he isn't right at his last spot; no area clear before looting (`meph.clear_before_loot`, about 12 s); no second look at an empty drop (2 s). **Check:** kill rate (was about 87%), deaths and drinks while looting, runs with `monsters at his body`. Baseline: fight median 24 s, dead to loot done 36 s. Next if these hold: shorter wait hopped away (1.5 s, maybe 20% of the fight; Blizzard may have a cooldown), and the retry after monsters at his body (51 of 62 still had monsters).

**2026-11-06 evening: using fewer rejuvs (Stephen OK'd).** Meph drinks after the kill only below 40% life, 25% mana (`meph.after_kill`; 82 of 175 drinks were after the kill, 2 of those below 40%). LK refill runs never drink, they flee or chicken (`town.refill_no_potions`; LK drank 42 of 78 picked). Not done, if rejuvs still limit: lower Meph's 60% fight trigger; Ormus healing potions for low life. **Check after some runs:** chickens on refill runs, deaths while looting, hours of Meph vs LK (was 3.75 h / 2.5 h).
East camp order is now ne, nw, nw_deep, matching the west, so no trip back to the fire between the hut's two chests. Untested live at commit time. Why: the fix was due once 1500 px of travel had built up, which fell between nw and nw_deep (19 of 19 runs in the east, 1 of 18 in the west).
Stephen also asked why LK only sometimes returns to the waypoint for Act 4: by design (`town_due`), loot to stash means the next game needs Act 3, so it exits on the spot.

**2026-11-06 11:56: filter changed, Meph running, Stephen away.** Detached `scratch/meph_then_lk.ps1`. Unified filter, for him and the bot: flawless + perfect gems only, all runes (r01-r33), runeword bases (`RUNEWORD_BASES` in `bot/chronicle.py`: Mancatcher 7br, Archon Plate utp, Monarch uit, Grim Scythe 9wc, Giant Thresher 7wc; temporary, normal + superior). Chronicle now 142 + 26 codes after his identifying. Backups `filter-20261106-115601`, `filter-repo-20261106-115600`. First live run of the full-stack fix too.
- **`filterEtherealSocketed`:** his Looting rule for these bases sets it, ours never did; meaning untested, so there's one rule each way. Check whether both survive the game's rewrite.
- **Known gap:** the bot's `white` label color needs V >= 200, so gray labels (socketed or ethereal items) are probably not picked. Not confirmed: no sample frame. Needs a real frame before adding a `gray` kind. Those bases still show for Stephen on his own runs.
- Base Diadems (ci3) added to `RUNEWORD_BASES`, and superiors removed since he socket-recipes these (`SUPERIOR_BASES`: only Diadem shows superior, for Charsi's imbue) (Stephen, 2026-11-06). Not installed yet: `python tools/chronicle_filter.py --install` once D2R is closed, before the next session.
- That session: stopped by Stephen's mouse at 13:53, 80/4000 ok. 21 Meph kills, then the rejuv refill on LK (27 to go). No full-stack event yet. Needs a frame of a gray label from him.

**2026-11-06 06:44: overnight still running.** 493 runs: 461 ok, 30 fails, 1 chicken, 0 deaths, 176 Meph kills. Refill cycle worked twice live, both ways (dry 20:09 and 02:17, Meph back 22:32 and 04:51): about 3.8 h of Meph, then about 2.5 h of LK. Drops needing identification are in the stash; no stack-full or stash-full events. No statue tooltips seen among Meph's stashed items: check.

**2026-11-05 22:30: full gem stacks handled, offline tests only; the running session still has the old code.** Before: a gem stuck on a full stack toured the stash pages, then set `stash_full`, which ends Meph and leaves LK picking runes only. Now: items whose tooltip says "Move to Stack Tab" never count towards a full stash; one retry, then gems and skulls are dropped (loot.csv: "dropped: its stash stack is full", first one per session saves frame `stack_full_dropping`). Orange names (runes, essences) are never dropped: they stay in the inventory with a warning. **Not known:** whether the game leaves an item in the inventory at a full stack or puts it on a stash page; only rejuvs have been seen stuck (Nov 3). The bot still picks up gems whose stack is full, then drops them. Gem stack levels not checked.
- Session so far: refill worked live (dry 20:09, LK from 20:11). Dry frame: empty Materials slots are dim purple ghost icons, probably what fooled the old check. Meph return not yet seen at 22:26. Drops: unidentified Amulet, unidentified Spiked Club (both Chronicle-eligible), Charged Essence of Hatred; LK: Gul, Pul. Item names are readable in `logs/loot/` tooltips.

**2026-11-05 18:18: Meph running, Stephen away (his call; Duriel recording later).** Detached `scratch/meph_then_lk.ps1`, log `logs/bot-20261105-181800.log`. Filter regenerated first: 149 unique + 27 set codes after his play. First live test of the rejuv refill if the stash runs dry.

**2026-11-05: GLaDOS prepared, nothing run there.** Handoff in `docs/glados.md`. Stephen wants it for bot runs while he uses Singularity, taking turns, never both. Syncthing syncs saves within minutes; he also has a scheduled backup on Singularity (last N saves per character). New: `config.local.yaml` (per machine, not in git), notes snapshot in `docs/notes/`, `logs/loot.csv` no longer tracked (local history kept).

**2026-11-05 morning (Stephen on the PC, offline work only; D2R closed):**
- Filter regenerated and installed: Chronicle 217/106, down to 151 unique + 28 set codes. Up to date, his rules kept.
- **Rejuv refill built, offline tests only (`bot/supplies.py`):** 2 zero restocks in a row (or both stacks empty) = dry; a boss session then runs LK until `town.refill_rejuvs` (40) are stashed, /players following, then bosses resume. Flags clear at session start, so rejuvs he adds by hand count. A dry stash saves a frame, `restock_dry`, showing the Materials tab: **read the first one** to learn why the old check saw a potion. Logs show the same stock-out on Nov 4 (`013833`: 49 zeros, `040055`: 28), with restocks working again after LK.
- **Duriel recorder ready, not run:** `record_duriel.bat` -> `tools/record_route.py --duriel --players 1`. Records from the spawn (so the Act II waypoint clicks are captured), F9 per new area = new canvas, F10 ends, folder `maps/<route>/duriel_route/`. Waiting for Stephen's time. Blizzaga can enter the chamber in Hell (Stephen, 2026-11-05).
- **Refactor view:** task plugins exist already (`bot/tasks`). No big rewrite. Split as Duriel forces it: boss fight/loot pieces out of `bot/meph.py`, generic routes out of `durance.py`, later `town.py` (1357 lines) by job. Stephen hasn't decided.

**2026-11-05 08:03: overnight Meph ended (Stephen's mouse): 251 runs, 171 ok, 42 chickens, 4 died, 34 fails. LK never ran.**
- **Rejuvs ran out at 00:01 (Stephen spotted it).** Every restock after that moved 0 potions (199 in a row), and nearly all chickens and all deaths came after it: before, 43 runs, 2 chickens, 86 % kills; after, 208 runs, 40 chickens + 4 deaths, 78 % kills.
- **Bug: no warning, no flag.** `restock_belt` only sets `stash_rejuvs_empty` when both slots read empty. Here it stopped at "nothing moved", so the first cell still read as a potion. Either the look-for-purple check is fooled by an empty or occupied cell, or clicks aren't moving real potions: not known, needs a look at the Materials tab. The Meph task also never reacts to a stock-out, which is why the fallback to LK didn't trigger.
- LK does refill: about 25 rejuv picks an hour (Nov 4, 04:00-07:00), `loot.rejuv_spares: true`. **Proposed:** a dry stash makes the bot run an LK batch, then resume bosses.
- Stephen has plenty of statues and essences now; he may want Diablo and Baal runs later, not decided as a bot task. **Next: Duriel** (he still needs that statue).

**2026-11-04 22:20: overnight run started (Stephen's call): Meph, then LK if it ends by itself.** Detached `scratch/meph_then_lk.ps1`, logs `scratch/meph_2220.log`, `logs/bot-20261104-2220*.log`. D2R was at character select, closed normally first. Filter updated through the page's own API, the first successful live Update filter: up to date, repo and live identical, Stephen's rules kept, 163 + 31 codes (Chronicle 204/103).
- **Stephen's next goals, in order:** (1) add Duriel to the task list, starting 2026-11-05; (2) later, the bot searches for a good LK map by itself; (3) later, it discovers all routes on a fresh map by itself. He expects to put Blizzaga into Nightmare by accident someday, which would destroy the current maps, so (2) and (3) are his insurance.
- **Morning checks:** statues still picked; no off-list uniques or sets; the LK switch if it happened. Gems can't spill: they're in stacks, like runes (Stephen, 2026-11-05); ignore the older "gem spill" checks below.

**2026-11-04 evening: web page extended.** Double-click `bot_page.bat` (password in `logs/web_password.txt`). New: Chronicle card (counts, missing list, whether the installed filter is current, Update filter button, refused while D2R or the bot runs); "Then LK" checkbox, same rule as `scratch/meph_then_lk.ps1`; a warning before Start if D2R is already open. Closing the page's window cancels a pending LK fallback.
- `chronicle_filter.py` now starts from the LIVE filter, so Stephen's editor changes stay (it used to overwrite them). His edits so far: `gems` category on Hide gems, new last rule "Show all Gems", cube gems rule removed. Now in the repo copy too.
- Checked with a real server while D2R was open: page, password, status, Chronicle numbers (204 uniques: it noticed a new entry), filter refusal. **Not run live yet:** Start from the page, a successful Update filter, the LK switch (unit test only). The bot page was "not yet used live" before this too.

**2026-11-04 19:56: stopped for Stephen (he needs the PC). No bot running, D2R closed.** 19:18-19:55: 16 runs, 15 ok, 1 "pushed off the spot"; 15 kills, 3 with a pickup (unique Poleaxe, an unidentified white label, Charged Essence of Hatred). The essence is still in Blizzaga's inventory: the next town stop stows it. Filter regenerated and installed; Chronicle unchanged at 203/103.
- Blizzaga's filter profile is LK Bot (bot-set, as usual); Stephen's own is "Looting". The bot sets it back each session.
- **Next session:** check for statues, off-list drops, gem stacks spilling. Launch: `scratch/meph_then_lk.ps1`.

**2026-11-04 19:20: the bot played the wrong character for ~80 s (18:46:10-18:47:30).** D2R opens on whoever was last played, and the bot pressed Play without choosing: it was on ThroatCutter (Stephen played it at 18:04). It stayed in Lut Gholein, and its walk clicks landed on an open Loot Filter window. Stopped by hand, left with Save and Exit. `ThroatCutter.d2s` differs from the backup only in 4 header bytes (offsets 13-14, 32-33; apparently checksum + last played), nothing else. Backup: `backups/20261104-184610`.
- **Left for Stephen:** `lootfilter.json` now maps ThroatCutter to LK Bot (no entry before), so that character hides most loot until he switches its filter back. The bot also leaves `/players` at its own value, as usual.
- Fix: `select_character` clicks the configured name on the menu; `check_character` confirms in game that its .d2s is the newest and otherwise leaves and stops the whole session. Offline tests; first live check is this session.
- The game dropped the rule "Show Chronicle missing set jewelry" on rewrite. Renamed: both rules it has dropped have 34-character names, a 32-character one survives (likely a name limit, not proven). That also explains the old rejuv/key rule vanishing.

**2026-11-04 18:50: Chronicle filter + all gems (Stephen's `Chronicle_Filter_Handoff.md`).** `tools/chronicle_filter.py` regenerates `filters/LK Bot.fltr` from the Chronicle: uniques and sets show only on bases that can still be new (164 + 31 codes, same as the handoff's snapshot). Existing pickups stay; every gem and skull grade added. Rerun after sessions, with D2R closed: `python tools/chronicle_filter.py --install`.
- **Filter puzzle, probable answer:** rarity + `itemCode` in one rule means OR, so the old BiS and Lidless rules showed all uniques and sets. New rules use `equipmentItemCode` (differs from the handoff, which said `itemCode`). Reasoned from the filter files, **not yet confirmed live**.
- Tests use a synthetic Chronicle: copying the real stash file into the repo was blocked, and the repo is pushed. The real file was checked read-only and matched (103/203/5).
- Live 19:18-19:40, running detached (`scratch/meph_1917.log`): the game kept every rule and code except the old rejuv/key rule. About 9 kills: mostly nothing shown but gold, then a white label, then a unique Poleaxe (`pax`, on the list; bot picked it). Fits the OR theory; the sample is small. Before: about 70 % of kills had something to pick up. Still to check: more on-list and no off-list drops, statues still picked, gem stacks don't fill and spill into the shared pages.

**2026-11-04 01:45: Stephen: Meph until the stash fills, then LK.** Running detached since 01:38: `scratch/meph_then_lk.ps1`, log `scratch/meph_0138.log`, no time budget. Ends Meph on a full stash or 6 failures in a row; LK then runs with `--stash-full-ok` (log `scratch/lk_0138.log`): a full stash no longer stops it, it picks only runes (no gems, uniques, sets). LK path with a full stash has only a unit test, not run live. F12, mouse or a web stop end everything, with no LK.
- Session 23:17-01:38: 57 games, 50 ok. Spill to shared page 5 works live (12+ times, nothing stranded).
- **Correction:** the "rune" pick count = all orange labels. All 9 since 22:30 were essences or Madawc's Ire, no real runes. "Meph 6 runes" below is unverified. `loot.csv` "item to shared tab" overcounts (a failed Ctrl+click is hovered and counted again per cell).
- **Filter puzzle:** about 51 of 65 sets/uniques since 22:30 have no "Eligible for Chronicle" line, yet "Hide all gear" didn't hide them. Installed filter = intended rules. Cause unknown.
- **Next, targeted loot (Stephen agreed it's possible; he will send more targets later):** a wanted-list file by base type + rarity; in town read the stowaway tooltip; keep wanted or Eligible, drop the rest; log-only trial first. Stephen believes the Chronicle fills on identification and is fine with duplicates: the chance of one mattering gets vanishingly small, so the Eligible line is good enough. Unidentified rings/amulets can't be told apart: keep them all.

**2026-11-03 23:18: Meph-only (Stephen's call: "continue to make improvements", LK when out of ideas or gold).** Running detached: `scratch/meph_then_lk.ps1`: Meph up to 6 h (stops on 6 fails in a row or a full stash), then LK up to 10 h. F12, the mouse or a web stop end it all, no LK afterwards. Logs: `scratch/meph_2317*.log`-ish, `scratch/lk_*.log`.
- Why: Nov 2-3 logs: Meph 44 kills = 6 runes, 19 uniques, 17 sets; LK 1540 passes = 6 runes, 992 gems, no uniques or sets (the filter's the same).
- `meph.fight_parked: true`: she fights him in the top centre after 3 rounds there. Before: 8 parked fights, 0 kills. 22:32-23:03: 12 games, 12 kills, 3 of them parked fights, no fails or chickens. The old rule came from the build without BO. Gives up after 12 rounds with under 5 % damage (`skipped`).
- **Lost loot found:** `find_labels` rejected a label touching another label or sprite (blob too tall). Logs/frames: at least a War Spear (21:01) and a Battle Axe (21:04) left on the ground, and a **unique ring at 21:24** (frame `durance3_auto/runs/1103-212258/loot.jpg`). Fix recovers stacked labels (4 real frames in `tests/test_labels_real.py`; 749 frames: only those 4 change). **The ring case itself isn't proven:** that frame is only saved small and my simulated sprites didn't recover. A kill with no pickup now saves a full frame: `meph_loot_empty`.
- Monsters still at his body after the hunt: she grabs what shows, then leaves (23:10 left a drop). Not confirmed live yet.
- Stash: shared page 1 and most of personal are full. Stowaway now spills to shared pages 5, 4, 3, 2 (these are Stephen's sorted pages, so loot will mix in) and the run stops when all are full. **Not exercised live yet.** `tools/look_stash.py` screenshots the tabs without moving anything.
- Gold 8.4M shared: not a limit. Open: the Act 3 town stall (`town waypoint not visible`), merc death cost, 35 s after-kill wait.

**2026-11-03 21:16, Stephen away, said to proceed: both fixes below checked live.** Detached `--tasks lk,meph`, `--max-minutes 60`, started 20:55: stops itself by about 21:55 (log `scratch/live_2055.err`).
- War cries: 19 casts in that session + 8 before it, no weapon warnings. The one chicken frame shows max life 618 (BO up; the 626 expected is close but not explained).
- Loot check: 1 live hit, right: gone at 0.15, 2 set labels, "dead", both sets picked (21:07). Fallback: 1 at 0.15 after 4 misses, nothing to pick up, so that kill is unconfirmed (21:15). No false "dead" seen yet; sample is tiny.
- New: parked Meph = result `skipped`, not `fail` (20:54: 2 parked games + 1 town stall hit the 3-failure limit after 9 min). Parked at 0.39 life in one game: she still gives him up.
- One Act 3 town walk stall at 20:50 (`town waypoint not visible`), next run fine, not investigated.
- At 21:15: 7 runs, 6 ok, 1 skipped, 2 Meph kills logged by the new checks. Totals after that not yet read.

**2026-11-03 18:30, Stephen back: no bot running until he says so. Next live session: confirm these two fixes first.**
- **Flail bug (Stephen saw BO fail in LK and Meph):** the swap key is a toggle and I counted presses. One lost press inverts every later swap: she stays on the flail, r/t do nothing. Evidence: max life 401 (flail, no BO) in 7 of 8 chicken frames from 17:58 on, which is probably why LK chickens jumped (17:17-18:26: 27 runs, 17 ok, 8 chickens, 2 fails, 9 Meph kills). Why the press was lost is unknown. Fix: `cast_warcries` reads the inventory tabs after each swap and retries, and only claims a cast if the flail really came up. About 1 s more per cast. **Tested offline only** (simulated toggle + real frames).
- **2 min searching for a dead Meph (18:24-18:26):** he died unseen at 0.21. Now: gone below 50 % + new non-white loot labels = dead; fallback after 5 misses below 30 %, 4 below 20 % (was 10 and 5). In all logs he only came back after 1-2 misses. Not done: death-animation detection (no frames of it). Most of the 2 min was grid searches and hunts; also no periodic hunt below 30 % now. **Tested offline only;** the label check has not seen a real Meph drop.
- To check live: `war cries` lines in the log, no `Call to Arms never came up` or `couldn.t confirm` warnings, max life 626 on chicken frames; Meph `loot dropped: dead` lines, and that no "dead" Meph is still alive when she hops over.

**2026-11-03 evening (Stephen away): respec + Call to Arms are in.**
- Hotkeys now: q Frozen Armor, w Energy Shield, e Static, **a Blizzard, d Glacial Spike** (they moved: the old config would have cast Spike as "Blizzard"), s Teleport, f Ice Blast. New: **r Battle Orders, t Battle Command** (t = Skill 9, bound in Options -> Controls; both bound in the skill picker). **F6 = weapon swap.**
- War cries can't be cast in town (red on the skill bar), so: on LK arrival; on Durance 2 arrival and at the Meph spot, again every 75 s of the fight. Life 485 -> 626 and it stays full. A run that ends mid-cast is put back on the main set next game (inventory tabs: II = orb + shield).
- Charms: the bot has no selling code at all; the only risk was the stowaway moving them to the stash. `inventory.protected` now matches the new layout (key at col 3 row 0, skull + 2 small charms below it, cols 4-9 yours) and a test pins it to a frame of your inventory. All still in place after the runs below. Rearranging them means updating that config line.
- LK/clear-a-chest attack is Glacial Spike (`hotkeys.attack`). D2R was at 1605x911: the bot now resizes it to 1280x720 at session start.
- **Meph with BO, 16:50-17:16: 9 starts, 6 kills** (fights ~15 s, HP mostly 93-99 %), 1 parked at top centre -> new game, 1 "couldn't get back from his platform", 1 cut by my own command timeout. No deaths or chickens. Was ~1/3 kills. Merc-tank test is still yours to watch whenever you like, but it looks less urgent.
- Shared stash page 1 is nearly full (Meph gear, plus ~30 potions on the right), so loot spills to your personal tab, which still has room. Worth a tidy when you're back; a full stash only means loot stays in the inventory.
- Running detached now: `--tasks lk,meph` for up to 4 h. Moving the mouse or F12 stops it.

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
- **Next for Meph (Stephen 2026-11-03: "definitely try the Merc tank next time I'm back at the machine"):** merc tanks Meph on his own side while she casts Static
  x2 then Blizzard/Frozen Orb. The south bank tops out around 1/3 kills because of the parking.
- **Fell back to LK runs 23:25** (Stephen: "fall back to LK runs, because we know those work"). By 06:05: ~440 runs,
  ~5 chickens, 1 town-WP fail; runes Um, Sur, Gul (04:25-04:40); many flawless/perfect gem picks.
- 2026-11-03 morning: Call to Arms made (Stephen will respec for the flail's Dex; then add BC/BO to LK + Meph).
  D2R was left at 1920x1080 after his play: closed + relaunched -> 1280x720. A stash left open hid the town WP:
  open_town_wp now presses Esc once first. LK 08:19-09:05 ~45 runs, 1 chicken; F12 by Stephen at 09:05.

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
Skills: see 2026-11-03 above (config `hotkeys`).
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
