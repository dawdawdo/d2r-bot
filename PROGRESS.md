# Progress

**Current milestone:** Andariel farming in the MF set (222 %), ~80 % kills, ~2.5-min runs; Act 1 town, poison cure, 15:45 fight setup: 86 % kills, ~14 kills/h (see 20:05). Mephisto is a real task now (branch `tasks`): `python -m bot.run --mode chests --tasks meph`
(or lk,meph). Phase 1 (LK) done: M0–M6 met. Proposed bar for v1.0: 100+ runs untouched.

**2026-11-23 22:30: state for the night.** Andariel since 19:12 (15:45 fight setup): ~76 % kills, ~12.5 kills/h.
Live tonight: terror check after the stairs + at the fight's start; antidotes in the inventory drunk; min_free 10;
failed pickups logged as left_<kind>; Akara's trade seen by the inventory panel (her tab strip varies). Gold: ~5 merc
revives/h, shared stash ~2.8M at 22:25 (~11 h): when it's empty runs switch to LK (gold_tasks, GOLD_LK_RUNS 10) and
try Andariel again every 10. Open for Stephen: stash rejuvs for Andariel (question at 15:15).

**2026-11-23 21:10: uniques left on the floor -> stash more often.** 19:41 and 21:01: three uniques each "picked" (labels
clicked) but never in the inventory (saves): 3 / 6 scattered free cells, no room for 2x3 / 2x4 items. Andariel
min_free 6 -> 10 (11 = empty loot area): stash whenever loot takes more than one cell. Pickups that fail are silent:
TODO log free cells before/after each pick. Finds tonight: Iratha's Collar (set), The Minataur.

**2026-11-23 20:05: the reverted setup holds: 14 runs, 12 kills (86 %), 1 miss, 1 chicken, 13.9 kills/h** (19:12-20:05,
no terror). Avg run 222 s (Akara refills after 3 potions add time). Gold: ~5 merc revives/h (50k each), 200k
withdrawals every 30-45 min; shared stash ~3.4M. Next by Stephen's order: success is good; speed (Akara stops,
walk-back misses); keep one change per clean hour.

**2026-11-23 19:50: the 18:00 hour was a missed terror zone.** "Terrorized: 93" in 5 of 5 fight frames 18:00-19:00
(none in any other hour today), but the check after the stairs read nothing: it took the automap frame before the
info text was up. terror_seen() waits for the text and looks again at the fight's start (fixtures info_terrorized_93 /
info_not_terrorized). So the 18:00 chickens were level-93 fights; the 17:00 slump (no terror) was the quick changes.
Also: 3 uniques left on the ground at 19:41 (inventory full; 4 antidotes from somewhere were in it, then stashed to
shared page 1): potion_kind now knows antidotes, the stowaway drinks them. Shared stash 3.79M at 18:50.

**2026-11-23 19:05: REVERTED the fight to the 15:45 setup** (commit b7422c8). By window: 15:45-16:44 14 kills / 18 runs
(78 %); everything after (search pattern, sooner search, last-seen search, keep-away 540, merc antidote) 18 / 38
(47 %). Kept: 9 s death wait, refill counter (Akara after 3 potions), automap fix. LESSON: one fight change per
clean hour, compared by window (runs.csv + logs); too many quick changes hid what hurt. Next: confirm ~78 % over
1-2 h, then try single changes again (keep-away 470?) one at a time.

**2026-11-23 18:20: EXPERIMENT running: merc antidote back on** (ANTIDOTE_MERC True). Since 16:55 also: search
pattern round the fight spot (SEARCH), search starts after 2 empty sweeps / 3 minion finds + 10 s, back to her last-seen
spot first; keep-away 400 -> 540 (bursts hit at ~406 / ~470); act detection waits for the automap; /players 1 from
the start. Per hour since 15:45 (kill/miss/chicken/merc deaths): 16h 14/3/1/3, 17h 9/5/1/6, 18h so far 1/1/3/2.
Compare the hour from 18:20 with the merc's antidote. Gold: withdrawals 15:26, 16:56, 17:31, 18:14 (~280k/h lately).

**2026-11-23 16:55: loot lost to chickens after the kill.** 3 today (15:08, 16:37, 16:49): her death clouds plus an
empty belt. DEATH_WAIT 5 -> 9 s; Akara refill after RESTOCK_AFTER (3) belt potions/antidotes drunk (bot.potions_used,
counted in the controller and andy.antidotes), since the belt reader sees only the bottom row. Watch: chickens after a
kill, Akara stops per run.

**2026-11-23 16:25: 85 % kills, 15.9 kills/h, no chickens in 13 runs** (since 15:45: /players 1 from the start,
act detection waits for the automap and falls back to the last act). SoJ projection at this rate: ~3,700 kills / 15.9
per h = ~230 h, ~10 days nonstop (was ~15). The rejuv question below is still open.

**2026-11-23 15:15: QUESTION for Stephen: stash rejuvs for Andariel?** Her resists are fine (poison 73 %, cap 75);
the problem is ~528 life and Energy Shield not taking poison. Long fights empty the belt (4 healing + 8 antidotes:
15:08 used 6 antidotes + 4 healing in 20 s, killed her at 83 %, then the death burst chickened her with an empty belt:
loot lost). Since 14:42: 7 runs, 7 kills, 2 lost to a chicken after the kill. Options: (1) a column of stash rejuvs
like Meph (instant heals; LK refills when dry, as for Meph) - my pick; (2) a lower chicken for Andariel (OK'd for Meph,
deaths acceptable) - only if the numbers say so; (3) gear with more life (Stephen's call). Also: runs.csv now records
"miss" (fight ran out, no kill); the bot page has a Miss column (Stephen read 155 "ok" as kills; 108 were).
Gold: merc revives (50k) + repairs ~270k/h; shared stash 4.59M at 15:30 (2.5M + 2.09M) = ~17 h of Andariel. When it's
empty the needs_merc guard fails every run and the session stops: watch on long soaks.

**2026-11-23 14:25: poison cure + Akara restock.** Stephen: priorities are success rate, then speed, then resources.
Every chicken frame today had a green (poisoned) life orb: orbs.poisoned + controller guard drink a belt antidote
when bot.cure_poison (Andariel's fight and loot); the stairs antidote stays, the timed 30 s round is gone. 14:13
chicken with "belt is empty": the half-used healing column was never topped up -> restock_at_akara: empty columns
get 4 of their kind (healing, mana, then antidotes), then healing and mana top-ups until one spills (drunk).
Since 12:56 (before these): 17 runs, 12 kills (71 %), 14.3 kills/h. Next: measure.

**2026-11-23 13:35: SOLVED: antidotes for Blizzaga only.** 12:56-13:30 without the merc's antidote: 9 of 11 kills,
0 never-seen, merc dead twice (revived at Kashya); with it (10:49-12:50) ~45 % kills, 10 never-seen. ANTIDOTE_MERC
stays False. Her antidote: at the stairs + once 30 s in.

**2026-11-23 13:00: (was OPEN) fights that never see Andariel.** Per hour (D kill, 0 never seen): 07-09h 19/24 kills, 1
never-seen; 10h 7/12 (3); 11h 4/11 (4); 12h 5/11 (3). Not the name check (logs/andy/names: the bar at her spot (639, 78)
read Ghoul), not the first position (first-snapshot similarity doesn't split outcomes). Streaks came with the merc
alive (revived 10:16; antidotes from 10:49: 0 merc deaths). In a 12:46 snapshot Blizzaga stood behind a big door with a
white automap cross ~300 px above her (the merc?). Experiment now: ANTIDOTE_MERC = False, fight start logs "merc
alive/dead"; compare ~15 runs. If the merc is the cause: hop toward his automap marker when she's unseen (verify the
white cross is him first).

**2026-11-23 11:50: antidotes, first numbers; walk back to the waypoint; fight searches past minions.** 14 runs with
antidotes vs 36 MF runs before: merc deaths 0 vs 7, chickens 2 vs 4, but kills 43 % vs 67 %: fights ran out never
seeing her (her bar 0 times in 5 of 6, 11:20-11:45); likely the merc, alive now, tanks her out of view while Blizzaga
shot minions at the entrance. Fix: 6 non-her finds and 20 s without her -> toward_throne (as after empty sweeps).
Town stops end with back_to_wp (stash label + (1012, 127)) instead of a fresh game. Belt: antidote columns never take
the last healing/mana column (_antidote_cols); a looted rejuv can fill an emptied antidote column (no stop until it's
drunk). Re-measure kills/hour (9.7 before antidotes) over the next ~20 runs; drop the 30 s antidote round if needed.

**2026-11-23 10:55: Act 1 town all live; antidotes (Stephen's idea).** Seen in real runs: Charsi repair, Kashya revive
x2 (widest menu line = Resurrect), Akara heal + potions, Act 1 stash stop (stowaway via open_stash_a1: 4 stashed, 22 s).
Fixed: the loop's periodic stow sent her to the Act 1 stash for nothing (now only < min_free). Antidotes: Akara (395,148)
puts them in the inventory, never the belt; buy_antidotes shift+left-clicks them into the belt (up to ANTIDOTE_COLS 2),
belt_kinds reads belt_antidote.png; andy.fight drinks one for her + shift+key for the merc at the stairs and again 30 s
in while she fights. To measure vs the morning: kills, chickens, merc deaths, Akara stops per run. Gold: two revives
(~50k each) left 5.6k carried; the next revive withdraws first. Rune names in the Act 1 stash's runes tab not read
("33 slots changed"): harmless, look later.

**2026-11-23 09:50: Andariel games stay in Act 1 (bot/a1town.py).** Act 1 spawns of a1_town tasks (andy) never
take the waypoint to Act 3: run.one_run calls a1town.town_stop (heal: belt, then Akara; stash when < min_free or
gold_needed: stowaway/withdraw/deposit through open_stash's Act 1 branch; Kashya revive; Akara potions when a belt
column is empty; Charsi repair), then a fresh game. Navigation: the town automap labels NPCs (map_<name>.png, 0.94-1.00
vs <= 0.53); the automap is 1/8 scale centred on her marker (642, 353), label +23 px = the NPC's spot; walk_to
re-reads it every step, detours +-60 deg when stuck (stone wall between the stash and Charsi), and walks toward the
stash/Kashya until a far label shows (~1,200 px range). Line clicks only after npc_<name>.png confirms the dialog
(Warriv's line 1 is Go East). Live via tools/a1_probe.py: stash opened, Akara healed, Charsi repaired. Not yet seen
live: Kashya's Resurrect (picks the widest menu line), Akara's potion buy. Fixtures: fixtures/a1town.

**2026-11-23 09:15: Andariel runs ~2.5 min (were ~4.5), button on the bot page, filter cut to Archon Plate.**
Every run had gone Act 1 -> Act 3 stash -> Catacombs because A2_MIN_FREE (12, sized for the tunnels' plates) > the 10-11
free cells with Gheed's in: tasks can now set `min_free` (andy 6). SoJ projection (drop tables, 222 % MF, p1, 80 %
kills): 1 per ~3,700 kills; at 4.5-min runs mean ~15 days nonstop (50 % by 10 d, 90 % by 34 d); faster runs cut that.
convergentblue.com /bot/: Andariel button (index.astro + worker TASKS, commit 8b7253c on main; build with
`PATH=/data/AutoDev/miniconda3/envs/node22/bin:$PATH npm run build`). Loot filter: RUNEWORD_BASES body armor = Archon
Plate only (Stephen 11-23); installed with D2R closed (old copy backups/filter-20261123-091113). Uniques this morning:
The Rising Sun, Kuko Shakaku. Stephen: Andariel runs should **never go to Act 3**. Left: Ormus heal/potions, Asheara
revive, Hratli repair, stash when < 6 free -> Act 1 equivalents (Akara, Kashya, Charsi, Rogue stash) to build next.

**2026-11-23 08:30: Blizzaga in her MF set (222 %), Andariel 9 kills / 11 runs since 07:41.** Stephen asked me to
swap the gear myself: tools/gear_swap.py (stash grid measured from a frame: cell (c,r) at (36.6+37.8c, 87.6+37.8r);
pick piece -> click slot -> old piece back in the freed spot -> safety click on an empty stash cell). Harlequin Crest,
Chance Guards, The Oculus on; Gheed's Fortune at inventory (0,0) (added to inventory.protected); Kira's, Magefist,
Eschuta's in her personal stash. mf.min.andy 200. First MF run: Statics up close, poison 91 -> 2 %: Static off,
potion at 75 %, chicken 55 % in her fight. Enigma (shared tab 5, Boneweave, str 164 >= 158) left out: it would replace
Skin of the Vipermagi's resists. Uniques so far: Manald Heal (stashed), The Rising Sun (amulet, 08:00). Fixed: tests
had overwritten logs/state.json's inventory baseline (now isolated, restored); Act 1 waypoint at the screen edge.

**2026-11-23 07:00: overnight Andariel tally (22:55-07:00): 105 runs, 46 kills, 0 deaths, 32 chickens, 5 fails.**
Loot: 11 runes, 3 unique picks (Manald Heal kept; the two at 05:40 likely failed: inventory full), 23 white, 1 gray, 1 key.
Since 05:00: session protection uses Stephen's last-played inventory as a baseline (back-to-back sessions carry it),
so the bot's own loot goes to the stowaway again (it had filled the inventory: gems, 3 Twisted Essences of Suffering,
a Northern Worldstone Shard, the Manald Heal; stashed 05:50). The loot clear hops off monsters instead of waiting
among them; the fight runs up to 60 s past its limit while she's in it. Open: chickens ~30 % (mostly her minions
near the door, sometimes right after the kill), merc dies most fights (50k revives; Asheara missed ~1 in 4),
Ormus misses cost town time. Next: MF gate once Stephen puts her MF gear on (then SoJ odds 1 in ~3,500 kills at p1).

**2026-11-23 05:00: Andariel ~60-70 % kills in the latest code; first unique: Manald Heal (03:38, ilvl 75, in
Blizzaga's inventory, unidentified).** 02:00-05:00 fixes: Act 1 spawn by the automap area name (area_town_a1/a3.png;
the Act 3 walks ran in the Rogue Encampment), Asheara: wider search region + second pass after re-walking the last
legs, belt-potion heal from a session's first run, keep-away 400 iso px (520 = never cast) not twice within 2 s,
Blizzard before each back-off, keep-away before the Statics too, hop back to the fight spot (dead reckoning) when
lost, one hop back right after the kill (death burst), inventory close re-checked after 0.4 s (lag reopened it over
the Act 1 waypoint and the Level 3 stairs). Supervisor on `andy`; restart helper in the session scratchpad.

**2026-11-23 02:00: Andariel 16 kills / 42 runs since 22:55; ~60 % in the latest code (3 of 4 01:33-01:52).** Added
overnight: wait 4.5 s at range for her death burst, clear minions round the body before looting, hop back toward her
after a life retreat, lost-low = dead under 40 %, inventory closed after war cries and per level (lag left it up and
hid the Level 3 stairs), repair via tools/repair_now.py. Loot so far: runes + whites (0 % MF; her magic/rares are
filtered). Recurring costs: merc dies most fights (50k revive; runs withdraw gold when a revive fails for it),
Ormus/Asheara/Hratli searches sometimes miss (retried in fresh games).

**2026-11-23 00:05: Andariel ~40 % kills.** 22:55-00:00: 17 runs, 7 logged kills (+1 more likely: lost at 21 %), loot
now works (2.5 s wait, two passes): rune + whites. Misses: she isn't found (search hop now straight up: every kill had her
bar at (639, 78)), or lost low (now: last seen < 35 % and gone 3 sweeps = dead, loot), chickens from her minions (fine).

**2026-11-22 22:55: FIRST ANDARIEL KILL; supervisor on `andy` (Stephen: keep pushing overnight, LK only if truly stuck).**
The merc had been dead all evening for want of gold on her (Asheara's dialog showed "Resurrect Waheed: 50000" with 0
carried; deaths drop it, and the run loop tries the revive before its stash withdrawal): tools/revive_now.py withdrew
200k and revived him. Next run: found her at ~(800, 97), Blizzard + merc took her 1.00 -> 0 in ~11 s, HP retreat once
(58 %), ended at 90 %, looted key + a white item. Stephen's plan in bot/andy.py: Static Field x2 when she walks within
300 iso px, then two hops so the merc tanks (didn't trigger: she stayed ~400 away). Players 1 (Stephen: forget 3).
Andariel fight chicken 50 %.

**2026-11-22 22:45: Andariel runs paused (LK back on for the night): 7 runs = 1 timeout with her at 22 %, 4 chickens
(life fell to 17-18 % before the check), 1 died (86 % -> 0 in ~7 s), 1 town fail.** Blizzaga kept all 12 items (save:
equipped 12, no corpse). Fixed during the evening: Ormus belt potions drunk in fights, buffs cast on Level 3 not at the
Level 4 stairs, terror check from the area info line, search hops select Teleport, isometric distance + one-hop retreat,
whole-view search, belt potions heal in town instead of hunting Ormus, Act 1 spawn told by its waypoint. **Next:** (1) merc
alive first: Asheara isn't found ("merc_not_resurrected", gold_needed set; stash has 7.6M); (2) the fight needs to stay out
of her poison: a fixed safe spot (like Meph's) to Blizzard from as she walks in, and earlier chicken in her room (her
poison outruns the 35 % check); (3) rejuvs back (LK save_rejuvs) before more Andariel; (4) players 3 + MF gate later.

**2026-11-22 21:50: Andariel task (`andy`) runs end to end; no kill yet. Supervisor on `andy` (Stephen: first runs at 0 % MF).**
Route: waypoint Catacombs 2 -> Level 3 -> Level 4 in ~35 s, every run since the fixes (bot/tasks/andariel.py: distance-
shortest stop path, legs that fall short don't stop it, take_warp hovers the stairs with the map hidden). The stairs were
found BY EYE: `--look-dir` frames (map hidden) show the railed stairwell going down; label scans had missed them for 3
causes: automap lines over labels (now `--map-off`), the stairs' hover spot is ~30 px tall (grid dy 28), and my seeded
"Level 1 stairs lead nowhere" entry made is_junk drop "... Level 3" too (now digit-aware). Level 2 exit world (-3753,-553),
Level 3 exit (1335, 260) from the arrivals. Level 4 (no automap walls in the lair; tools/andy_probe.py): the stairs room opens
west through a door (3 hops left), then up-right toward her throne (red carpet, pillars); she walks out to meet you.
Fight (bot/andy.py): sweep rings for name bars (name_andariel.png; any monster gets Blizzard, her first), Blizzard /
Glacial Spike from > 400 px, two hops back when closer or under 70 % life; loot where she was. Run 21:11 took her to 47 %
before a poison chicken (merc dead, bought potions not drinkable then: fixed `keep_vendor_potions`). 21:17-21:44 chickens:
Level 4 was TERRORIZED (level 93, 100 -> 48 % in 3 s): the arrival banner is now checked (TerrorZone -> wait for the hour).
Open: merc dead (Asheara/Ormus not found by the town walk tonight; stash gold 7.6M fine); rejuvs 0 (Ormus mixed potions
instead, needs_rejuvs False); `andy.players` 1 for testing (3 planned); add `andy` to mf.min once she has MF gear.

**2026-11-22 18:00: Andariel task started (Blizzaga, MF gear, players 3); Catacombs Level 2 stairs down NOT found yet. LK running.**
Why Andariel: D2R gives her the quest drop on every kill (monstats: all her Hell TCs = `Andarielq (H)`), so she drops 2-3x
the rings of Mephisto. SoJ per kill (d2data 2.x TCs, xl uniqueitems; scratchpad soj_odds.py): 280 % MF players 1/3/7 =
1 in 3,500 / 2,500 / 2,200; 0 % MF p3 1 in 5,700; Meph 280 % p1 1 in 7,800. Plan agreed with Stephen's lean: Blizzaga (MF
280 %, FCR 136 = 8-frame teleports) not ThroatCutter (60 % MF, 13 frames, melee = new combat code). Gate on MF like Meph.
Done: `wp_catacombs_2` (Act I tab, 9th row) + Act 1 spawn shortcut in `to_durance2`; `area_catacombs_2.png` and `area_is`
checks the last digit (Level 2 vs 3 match 0.96 on the whole name); tools/cata_probe.py, tools/cata_goto.py (go to a world
point of a learned map, dense label scan). Finder (tools/find_tunnels.py) fixes, all opt-in flags: `--label` (tooltip
must contain "Catacombs Level"; the waypoint label and floor potions are as wide), `--max-h`, `--map-off` (automap lines
across a label break find_tooltip's black box: with the map on, only the waypoint room, which has no automap walls, gave
labels), `--marks` (level exits are purple wall segments on the automap; 62 views agreed on the Catacombs Level 1 stairs),
`--void`, `--frontier-wall`, `--seconds`, `--dx/--dy/--abort-hp`, BO + armor/shield refresh before scans (BO lasts ~90 s:
every chicken frame had max life 348). AutomapOdometer rejects fixes that jump > 700 px beyond the commanded hops (same-
looking corridors aliased 3,045 px). ensure_automap closes a stray inventory panel.
Cata 2 result: 269 stops, the whole automap maze visited, teleports outside it all fail; only one exit mark (Cata 1 up
stairs at world (-3538, 1037) from the waypoint). Map-hidden rescan 2/3 done (87 stops left, in the south where every game
chickened). Cost: Blizzaga's rejuvs 14 -> 0 (belt + personal stash; shared stash still 1 + 1), armor icon red (repair due).
**Asked Stephen:** walk Blizzaga once from the Cata 2 waypoint down to Cata 4 (or say where the stairs are). The exits he
takes should then show as purple marks, and `--marks` goes straight to them. Until then: LK (rebuilds rejuvs).
Resume: `python tools/find_tunnels.py --map-off --marks --games 1 --hops 400 --seconds 400 --dx 100 --dy 60 --abort-hp 8
--dest wp_catacombs_2 --style tunnel --areas catacombs_2 --folder cata2_auto --goal catacombs_3 --min-w 150 --max-w 360
--max-h 34 --label tt_catacombs_level.png --frontier-wall 0.15`

**2026-11-22 11:30: Armor Stands are the base source; bases now flagged from the saves.** 9 white armor bases (Balrog Skin x4 incl. eth + 4os, Boneweave x4, Loricated Mail), all ilvl 79, came in the first day of stands vs 0 in 11,840 chests. The screen log calls any white non-key/rejuv pick a "gem". New `bot/bases.py`: each session start diffs the new backup against the previous one and logs "new base: <name> (eth, N os, ilvl, def) in <tab>" + appends logs/bases.csv (includes Stephen's own finds between backups). History: `python -m bot.bases --all`. Next after Stephen's plan: Andariel (his SoJs); bot stopped while he plays.

**2026-11-22 10:40: save reader is pure Python now (bot/d2save.py); MF gate and session protection work on Singularity too.** d2dump was a Linux-only Rust binary (crate d2s 0.1.1). Ported its read side line by line; same JSON shape. Checked against d2dump on every backup: 608 unique .d2s/.d2i files (15,910 copies), all identical field for field; armory rebuild from 20261122-093230 identical (saves, inventory.json, pagedata except 'built'), 0.4 s vs 1.1 s. Read-only: it never opens a file for writing and reads only backups/. Game tables: txt105/ + xl/ from the tracked armory bundle, extracted on demand (no binary). Bot stopped 10:07 on GLaDOS: Stephen plays on Singularity.

**2026-11-21 09:20: Armor Stands live; runes below Amn dropped; gold is one shared pile.** rack_probe found an Armor Stand outside, NE of each camp's west hut (bonfire + (-305,-677)); after nw_deep she teleports to (-305,-567) and clicks it (features.armor_stands, tt_armor_stand.png). First run: both stands clicked. Runes El-Thul: hidden by the filter (installed) and never cubed (cube.bottom_rune Amn). Keys: none stashed since the 11-20 fix (the 48 were older; Stephen cleared them); 3 key stacks now sit in his protected inventory cells, ignored by the bot. Shared stash gold is one pile (Stephen), not per page. Probe runs have no BO unless cast (fixed in the probe).

**2026-11-21 08:50: hung D2R cost 5 h; supervisor now restarts the game after a failed session.** 03:25 D2R stuck on a loading screen; every session until 08:43 failed against the same hung game (no restart after bad sessions). Fixed (35c6a60), supervisor restarted 08:45 with the new code. Overnight 23:15-03:25: drained the ~36 rejuvs in the stash (Stephen's play?), found 15; 18 chickens, 2 deaths (00:06 real, max life 346 = no Battle Orders though 'war cries cast' was logged; 03:15 champion Doom Apes 58% -> 12 life). save_rejuvs mode started 03:25 (refill_left 20) but no runs since. Next: verify BO actually landed (max life in the 'Life: x / y' text, recast if missing); cast_warcries only checks the weapon swap. Armor Stands: Stephen doesn't know where; none in LK huts.

**2026-11-20 23:30: features.save_rejuvs: 20 (LK-only refill).** Drinking at 60% cut 'belt is empty' 119 -> 13, but 18:11-23:10 still 34 drunk (12 on the way out of a chicken) vs 18 found. With the stash dry, LK-only sessions now don't drink in runs (flee/chicken) until 20 more are stashed (the belt fills first), then normal. The on-the-way-out drink stays (11-06 death). Chicken frames: melee packs at the camps; one had max life 327 not ~510 (BO missing). Stephen saw a socketed Boneweave himself (filter OK) and still wants Armor Stands: none in the LK huts, need a place.

**2026-11-20 19:00: LK chests apparently don't drop white bases (Stephen: chests drop magic items only).** Since 11-16: 11,840 LK chests, filter shows 19 white elite bases + Diadem, and every stashed item's tooltip (logs/loot/) was checked: no stashed item without the stack-tab line except keys. The one white Diadem (ilvl 85) came from the 11-13/14 tunnels runs. Classic tables say ~6 expected; seeing 0 is ~0.25% luck. Racks: rack_probe found only Weapon Racks (weapons only) in the 6 hut spots, no Armor Stands. Check script idea: template-match 'Move to Stack Tab' in logs/loot tooltips; misses = gear.

**2026-11-20 18:10: drink at 60% (was 70%).** Gold off didn't fix chickens (22% today): the cause is an empty belt (stash rejuvs dry since 11-14; 'belt is empty' before nearly every chicken). Today ~62 rejuvs drunk vs 28 found; finds are steady at ~4 per 100 chests, but chickens cut chests/run 5.5 -> 3.9. Next if still short: refill mode (no drinking) until 20 in stash. Bases: Act 3 (H) Chest C includes Equip B -> armo/weap TCs, so super chests can drop bases (rare); racks probed so far are Weapon Racks (weapons only), no Armor Stands found. Stash has no white armor bases yet.

**2026-11-20 11:40: `features:` block in config.yaml (Stephen: make the extras toggleable).** One switch each:
gold_pickup (OFF: rebuild rejuvs; stash rejuvs went 21 -> 83 on 11-12/13 with LK alone, empty since the 11-14 Pit tests
and the gold-era chickens), gold_deposit, weapon_racks (off), gems_and_bases, charms, spare_rejuvs, war_cries, cube,
act4_exit, wait_out_terror, skip_huts (list of LK targets). `bot/config.py` FEATURES maps them onto the old keys
(loot.pick_gold, lk.racks, ...); those were removed from config.yaml; a typo'd feature name is an error at load.
New code switches: gold_deposit, war_cries, skip_huts. Restart the bot after a change.

**2026-11-20 10:40: chickens traced to chest gold; gold picks now careful.** Stephen: no potion buying; get back to
rejuvs > use. Chickens were 3-5 % through 11-12 and 22-32 % from 11-15, the day `loot.pick_gold` went in. Potion/
chicken/empty-belt events right after looting: 0.03/run (11-09..11) -> 0.25/run (11-17..19); others ~2x. Gold stays
(Stephen wants every tab full) but `lk.under_attack` stops the gold picks when life < 90, life -5 or mana -10 (energy
shield) since they started, and piles > 260 px away are left (`loot.gold_max_dist`). **Check:** chicken % and
rejuv picks vs drinks per day (runs.csv + "-> potion" log lines) over the next day; target back near 5 %.

**2026-11-20 09:00: racks off (speed).** Last 343 runs: 80% ok, 18% chickens, mostly with an empty belt
("belt is empty" ~140x a night: LK is chest-rejuvs-only, stash out of rejuvs). Typical run 122 s = menu 17 + town 33 +
war cries 4 + LK 55 + exit 13. Gold picking stays ON (briefly off; Stephen: fill every tab, shared + personal. 11-20 10:05 save: shared pages
2.5M, 2.5M, 1.47M, 0, 0 (a deposit overflows to the next page), personal 87k, carried 200k); `lk.racks: false` (489 clicks, 481 nothing). **Revisit racks** (Stephen 11-20) if LK chests still give no base by ~8,000 chests. **Asked Stephen:**
buy healing potions for LK (Ormus) or chicken at 40% instead of 50%? Until he answers: unchanged.

**2026-11-20 07:40: keys in the stash again: fixed (2nd cause).** 4 key stacks reached shared page 1 overnight
(save diff 21:17 -> 02:46: only those 4 keys were new there). Not the 11-19 drop-with-stash-open bug: the stowaway's
inventory scan used a frame from before the panel was drawn (GLaDOS lag) -> 0 empty cells, everything "loot", so the
key stack was Ctrl+clicked in with the loot (logs/loot tooltips show "Key" at (3,2)/(3,0)). Fix: `_scan_inventory(wait_open=True)`
polls `inventory_open` first; the per-item hover frame skips any key stack (log "is a key stack, not loot").
Night 11-19 21:17 -> 11-20 07:20: 240 runs, 193 ok, 40 chickens, 1 death; Ohm, Sur x2, Hel x2, Lem, Lum x2, Dol (Ohm/Sur/Hel/Lem/Lum/Dol
verified in the save). No bases yet. Racks: ~45/47 "nothing wanted" in the first hour (keep watching).
**Base odds corrected (11-20):** the 11-19 figures (Mage Plate 1/1384, any 4os armor 1/173) were ~5x too high. Redone
with NoDrop 100 / Picks 4 / quality rolls at /players 1 (scratchpad chest_odds.py on the d2data tables): the 9 droppable
filtered body bases together ~1/1800 chests (~1.4/day); Mage Plate 1/6600, Dusk Shroud 1/26500, Boneweave 1/10100.
Cross-check: model says ~4 white Grim Scythes in the 22,636 chests since 11-06; ~2 found. (Runes run ~10x the model,
0.06/chest: D2R rune tables differ; bases don't follow.) Pipeline verified: filter installed + selected, white bases
picked and stashed before (9wc 11-15, ci3 11-14). **Check:** no base after ~8,000 chests (P ~1%) = look again.

**2026-11-19 21:15: Weapon Racks in LK (Stephen OK'd).** Probe (`tools/rack_probe.py`, scratch/racks*): both NE huts
have a Weapon Rack at the same offset from the bonfire (BONFIRE_LAYOUT ne.rack = (558, -512)). **No Armor Stand** on
this map (maxroll puts one in the 2-chest hut; the long hut here has only "Stash" objects). After the NE chest,
`_visit` hover-scans 105 px for the rack tooltip (`tt_weapon_rack.png`), clicks it, loots (log "rack: ..."). Toggle
`lk.racks: false`. A probe click on the west rack showed a "...Scythe" label (filter shows only Grim Scythe): racks may
feed the Insight bases. **Check:** "rack:" lines, `rack_not_found` frames, run time (+~5 s).

**2026-11-19 20:35: all elite body armors added to RUNEWORD_BASES (Stephen), filter installed, LK running.** Note: the session-start "unprotected items" warning also lists loot left in the inventory at exit (gems): expected.

**2026-11-19 20:15: Stephen's layout changed again; charm + skull stashed and put back.** He played on Singularity
18:54-19:36. The first stash stop (20:00) stashed Gheed's Fortune (col 4, outside the 11-15 box) to the personal tab
and his Flawless Skull ((3,3)) onto the Gems tab. Both put back by hand (stash_probe). `inventory.protected` now
[[4,0,6,4],[3,3,1,1]] (fixture `layout_20261119.png`). **Guard:** at session start `run.protect_own_items` reads the
backed-up save (d2dump, same read as MF) and adds any charm/tome/cube outside the box to `protected` for that session,
with a warning; other non-key items outside it are logged ("the stowaway will stash them"). (Both machines since 11-22.)

**2026-11-19 19:50: Mage Plate + Dusk Shroud bases; screensaver wake.** Stephen wants Enigma (3 os) and CoH /
Fortitude (4 os). From the game tables (scratchpad d2data, 2.x): LK chests are `Act 3 (H) Chest C` -> Equip B, top
armo75, so Archon Plate (qlvl 84) can't drop there; Mephisto (H) has Magic 1024 in his TC, so he never drops white
items. White-base odds per LK chest (0 MF, ilvl 80): Light Plate 1/843, Mage Plate 1/1384, Dusk Shroud 1/5472, any
white 4-socket body armor 1/173. At ~2,600 chests/day that's about 2 Mage Plates and one Dusk Shroud every 2 days.
`xtp` + `uui` added to RUNEWORD_BASES, filter installed. **Also:** a remote stop at 18:54, the screensaver came on
after 15 min idle, and the 19:38 remote start failed twice (Battle.net stuck on its Login window until the screen woke).
`bot.io.linux.wake_screen()` now runs before every launch (`cinnamon-screensaver-command -d`; lock is off).

**2026-11-19 12:00: gold deposit; key leak #2 fixed.** Blizzaga carried 910k (her max). town.deposit_gold at the stash stop
after `stash.deposit_after_picks` (25) chest gold piles: shared tab -> coin left of the inventory gold box (the number is
only a tooltip) -> Deposit box (prefilled with all; template deposit_dialog.png) -> OK; still carrying -> personal tab, same;
still carrying -> both full: bot.gold_full / state gold_full, no gold picking, retry every 6 h. 12:15: due once she carries
the max (lk._gold_at_feet: a pile stays under her twice -> bot.gold_maxed; backstop 200 piles); all in, then 200k
(stash.keep_gold) typed into Withdraw. Frames on GLaDOS lag the game ~1-2 s: every step waits on a picture (Deposit /
Withdraw box templates, carried / stash gold boxes). Live: shared 685,976, carried 200,000. All live-tested (shared,
personal; gold moved back: shared 910k, personal 19). Keys: 170 more on shared page 1 since 11-16: about 1 drop in 10 went
into the stash (a lost Esc left it open; Ctrl+click with the stash open = stash). town.drop_cells now checks the stash is
closed before and after opening the inventory. Cleared the 21 stacks live (moved out, dropped).

**2026-11-17 09:25: cube up through Ist; Ist+ never inputs.** cube.top_rune Ist, NEVER_FROM Ist (hard floor), Fal..Mal
recipes added (Flawed Ruby/Emerald/Diamond, Topaz, Amethyst; 2 runes from Pul up). Rune recipes may use any gem down to 0
(gem_keep 0, Stephen 11-17: "they will be replaced"); gem upgrades keep 10 of every gem (cube.gem_reserve, Stephen 11-17). Ctrl/shift+right-
click triples OFF: each try moved 3 runes to the inventory (stowaway put them back, nothing lost; the "3 short" diffs).
Amn ~32 / Thul ~27 wait on Chipped Amethyst / Chipped Topaz (0: only from drops, used as soon as one arrives). Never cubed above
Fal before today; first cube with these rules 10:11 (4 Ist, 5 Lem, 5 Um, 2 Mal). The tab read Lem 12 as 2 (leading 1 lost on
the icon): the cube now floors its tab read with the save-file counts (armory/pagedata.json) when that save is newer than
the last cube. Ohm has been 2 since 11-09; Sur 8 (bot picks 11-10, 11-11, 11-16, 11-17).

**2026-11-15 21:05: Stephen's notes fixed; LK running.** (1) Keys: the inventory `protected` box was still the 11-03
layout. Stephen's col 3 is empty now, so key stacks there were invisible -> keys_left 0 -> keys bought every visit; 199
keys reached shared page 1 (08:00-15:36; he cleared them). Loot in col 4 (rune, diamond) was never stashed either. New box
from the 20:52 save: [[5,0,5,4],[4,1,1,1],[4,3,1,1]] (charms, tomes, cube, his skull). (2) Gems: Flawed Sapphire 99 /
Topaz 85 / Amethyst 69 = rune-recipe gems (Ko/Io/Lum), never cubed. Now 30 kept (cube.rune_gem_reserve), rest cubed.
(3) Shift+right-click (3 into the cube) added but moved nothing live (21:17, GLaDOS): falls back to single clicks; first
cube after the fix: 146 transmutes in 708 s, all counts as planned. (4) Mancatcher off
chronicle.RUNEWORD_BASES. Cube triples now try ctrl+right-click, then shift (21:48 session). **Planned, NOT now (Stephen 11-15: "I'd like to try it, but definitely not right now"):** Chaos seal-pop task:
River of Flame WP -> 5 seals by template, kill 3 seal bosses, wake mobs, pop the last seal, loot, save & exit before
Diablo; pop deaths use normal monster drops (white Archon Plates possible); LK fallback, < 50 % clean -> LK.
Start only when Stephen says so. LK keeps running.

**2026-11-15 09:50: LK picks chest gold; Stephen farms the plates himself.** loot.pick_gold (lk._pick_gold: up to gold_max_picks=8
piles per chest after the items, biggest first, not in the picked list; live: 1-5 clicks per chest). town.revive_merc: a failed revive
right after a withdrawal sets state stash_gold_empty -> no more stash trips (cleared by a successful revive). Stephen: keep LK running,
he farms Archon Plates by hand; don't restart Pit/tunnels unless asked. **Next:** watch that the merc gets revived once she holds 50k.

**2026-11-15 08:05: Pit stopped, LK running. GOLD IS GONE.** Shared stash gold 3.86M (11-14 04:40) -> 0 (11-15 07:57); Blizzaga holds 16.
Pit 14:21 -> 07:49: 188 runs = 38 ok / 119 chicken / 11 died / 20 fail (20 % clean, 17.5 h), no Archon Plate. ~30 withdrawals of 200k:
each death drops the carried gold. Since ~05:50 the merc stayed dead (no 50k), so no Insight and almost every run chickened.
Bug: town.withdraw_gold never checks that gold arrived (empty stash -> walks to Asheara + stash every run). Per Stephen's rule
(< 50 % clean -> LK) the supervisor is on `lk` since 08:01. **Open question for Stephen:** plates plan (Pit at /players 1-3 once
gold is back? carry less gold per withdrawal?).

**2026-11-14 21:10: Pit results + vendor idea closed.** Pit with the potion stop (db1e679), Act 1 shortcut (d4b0a28) and map_text_open
0.5 (65a506e): 14:21-20:48 = 16 ok / 41 chicken / 2 died / 8 fail (24 % clean; tunnels 21 % with ~1 death in 8). Finds: gems, rejuvs,
two white Mancatchers, no Archon Plate yet. Stephen: Pit "going kind of ok" -> it stays the plate farm. **Charsi check dropped:**
Arreat Summit + the diablo2.io shopping guide say Act 1/2 Hell vendors never sell exceptional/elite, and above ilvl 25 (clvl 20) vendors
sell magic items only (no white/socketed) -> no vendor can sell a runeword Archon Plate to Blizzaga. Matches the Hratli probe (all magic).
**Next:** fewer Pit chickens; Pit Level 2 (stairs not searched); then Andariel (rings).

**2026-11-14 13:35: Pit task runs (entrance found by the bot).** `--tasks pit`: Outer Cloister WP -> lead-in "-340,200,10;0,290,5" (Monastery
Gate -> Tamoe Highland) -> entrance warp in maps/<route>/pit_tamoe2 ("To The Pit Level 1", 188 px, world (-3018, 1263)) -> Level 1 with
tunnels.farm_tunnels(style="gray", folder=pit_auto). maps/<route>/pit_auto/route.json makes it ready. ~90 s to inside, 2/2 entries.
Supervisor on pit since 13:32; LK ran 09:55-13:10 at ~87 % clean (95 ok / 12 chicken / 2 fail). Verdungo's -> ThroatCutter (Plan; Stephen
moves it). **Next:** measure Pit clean rate (Stephen: < 50 % -> LK; tunnels were ~21 %); Charsi armor-tab check; Act 1 spawn shortcut
(Pit.a1_start is set but run.py doesn't use it yet: games go via Act 3); Pit Level 2 (stairs not searched).

**2026-11-14 09:50: Pit entrance NOT found yet; LK running as the fallback (Claude's usage limit reached, session stopped here).**
Tried: probes S, E, W from the Tamoe entry (walls/woods, no cave: maps/<route>/hop_probe/*/sheet.jpg); searches pit_tamoe (72 stops,
drifted W, only a shrine) and pit_tamoe2 (8 games, 74 stops, lead-in "-340,200,10;0,290,5", no tooltip 150-420 px). Most games ended
in chickens (Tamoe packs), so coverage is thin. Next: draw pit_tamoe2/automap.png with stops to see what's unexplored; try min-w 100
(the cave label may be short); ask Stephen for a closer landmark. Still to build: Pit clear loop (copy tunnels.farm_tunnels), Charsi
armor-tab check (tools/vendor_probe.py logic, Act 1), route.json so `pit` is ready. Supervisor: `--start lk` at 09:50.
**Open questions for Stephen:** (1) Verdungo's in shared tab 2: Blizzaga or ThroatCutter? (2) Pit: what does the entrance sit next to in
Tamoe Highland on your map (how many teleports from the Monastery Gate, which way)?

**2026-11-14 08:45: Pit in progress (Stephen away ~8 h, said: keep going, cache questions).** Plan: `pit` task + Charsi armor-tab check
per Pit game (buy socketed or white Archon Plates). Done: Act I WP points (Black Marsh, Outer Cloister verified), open_a1_wp / act1_to,
"gray" automap style, area templates black_marsh / tamoe_highland, automap_shown also by the "Difficulty: Hell" text
(automap_difficulty_text.png; NOT difficulty_hell.png = the Hell button), find_tunnels generalized (--dest/--style/--areas/--goal/
--pre/--min-w), tools/hop_probe.py. Route so far: Outer Cloister WP, 12 teleports (-340, 200) through the Monastery Gate into Tamoe
Highland (Stephen's hint: Pit is SW of the Outer Cloister, more S than W), then search SSW (maps/<route>/pit_tamoe). Site has a Pit
button; not-ready tasks run LK. If the Pit stalls (Stephen): tunnels first, but under 50 % clean runs -> LK (runes for the Chronicle).
**Open questions for Stephen (non-blocking):** (1) Verdungo's in shared tab 2: Blizzaga or ThroatCutter?

**2026-11-14 07:20: overnight tunnels.** 67 runs 23:12-07:20: 14 ok, 38 chicken, 11 "died" (~8 real, 3 the exit bug), 4 fail (gear always recovered: corpse pickup
at the next spawn works; a mid-cycle backup shows her naked with a corpse, that's normal). No Archon Plate. Big-pack evasion (21:50) was
wrong: nav.movers counts effects, it fired at full HP every stop -> OFF (BIG_PACK 999). **Exit bug fixed (stuck 06:17-07:00):** at ~8 %
life the orb reads as dead, the "dismiss death screen" Esc opened the game menu, the next Esc shut it, and "Save and Exit" clicked the
Kurast Docks waypoint she stood on (wp_menu loop). Now: that Esc opening the menu = alive -> save & exit; an open WP panel is closed
first; ensure_main_menu Escs a WP panel. Supervisor restarted 07:01 (pid 117428, same autostart command) to reset its backoff.
**Decision for Stephen:** AT ran ~21 % clean overnight with ~1 death per 8 runs; Pit route (same per-kill odds, weaker monsters) is the
remaining lever; vendors measured out.

**2026-11-13 22:50: where white Archon Plates can come from (math on D2R tables, blizzhackers/d2data; scratch calc).**
Per regular kill at /players 7: AT ~1 in 4,200, Pit ~1 in 4,400. Champions/uniques and Mephisto: never (their TCs force magic+).
No white->exceptional/elite cube upgrade in D2R (only unique/rare/set). Vendors: no vendor stocks utp; only a Hell elite roll on
Light Plate stock (Elzix, Charsi always 1 Studded Leather -> Light Plate; Jamella/Anya sometimes) could make one. Measured
(tools/vendor_probe.py, 6 games Hratli): ~30 armor items, all magic + normal tier, 0 elite -> vendors not worth building.
Estimate: AT ~14-29 h per white plate at the current kill rate, Pit maybe 8-14 h (needs a route). The socket recipe rolls 1-4
(assumed uniform): ~4 white plates per 4-socket one. Stephen: any socketed Archon Plate is fine to keep.
Belt: big packs (10+ movers) now evaded instead of fought (21:50).

**2026-11-13 20:50: tunnels potions + evening fixes.** Clean runs fell from ~75 % (12-14 h) to ~20 % (18-19 h): the rejuv belt ran dry
at 14:28 (main cause), plus my bugs (struck-rule change, reverted; a chicken swallowed as "fix lost"; BO refresh counted from the
farm start so BO lapsed mid-fight, 507 -> 345 life). runs.csv records picks only for clean runs, so chicken-heavy hours look lootless.
Stephen OK'd buying potions for tunnels (belt only, **never the stash**) and picked **2 healing + 2 mana**. Two buy spills stashed 11
potions on shared page 1 (removed by hand and drunk, 20:10). Now: Ormus stop when the belt has an empty column (Act 2 spawns with 2+ empty
go via Act 3), plain single buys with a delayed inventory check (stops at the first spill), up to 3 fresh-game retries when Ormus is missed
(not a gold problem), stowaway drinks inventory potions (`vision.inventory.potion_kind`, 0.08), tunnels keep belt potions (no town
drinking), a buy that finds him but buys nothing sets gold_needed (0 gold after deaths). War cries every 60 s from the real cast. Empty-belt
chicken 60 %. First full cycle 20:40 worked: belt hp/mp/hp/mp, the 13th potion drunk at the stash.
Answered: Monarch off the filter; ThroatCutter BiS steps on the Plan; site task buttons single-choice; DClone = sell an SoJ (SP).

**2026-11-13 15:40: tunnels running unattended, tuning for smooth runs.** Since 11:40 ~35 runs: ~70 % clean; rest chickens + 1 death.
Finds: Monarch (11:51, now off the filter: Stephen has enough Spirits; Mancatcher stays), Northern Worldstone Shard, flawed gems,
rejuvs, gold. **No Archon Plate yet.** Added today after the first version: Act 2 spawn shortcut (`run.a2_start_ok`, 12+ free cells:
Lut Gholein WP -> Lost City, ~70 s vs ~3 min), 12 picks/stop, cursor parked before Alt scans (urns / "To The Lost City" read as labels),
monster bar ignored to y 95 (its "Immune to ..." lines read as set/rune labels; the 4 "set"/"rune" picks of 12:3x-12:52 were that),
evade when struck (to visited ground, 90-degree fallback, no fight right after), end the run on arrival < 70 % with an empty belt,
automap state by the area name (`tunnels.map_open`; pixel counts misread effects), lost-fix recovery, safety exceptions never swallowed.
**Open question for Stephen (not blocking):** the belt is empty (rejuv stash dry, tunnels skip the LK refill): buy healing potions
from Lysander for tunnels, or interleave LK refill runs? Until answered: tunnels as is.
Next: ThroatCutter BiS steps added to the Plan (site); after the plates a ring task (Andariel); DClone = sell an SoJ in SP.

**2026-11-13 11:40: `tunnels` task live, unattended session started (supervisor, `--start tunnels`).** Stephen: Archon Plates are
the priority, **4 minimum, probably more** (cube rolls); runs must not stop early (memory). `bot/tasks/tunnels.py` + `bot/tunnels.py`:
enter = WP Lost City -> Trap Door (two clicks) -> inside (~90 s from game start); farm (`tunnels.farm_s` 240) = explore the tunnels'
automap frontier, later tour known stops (`maps/<route>/tunnels_auto/`), at each stop `engage` (Blizzard / Glacial Spike at the
nearest mover, stops below 30 % MP) then `loot_here` (automap off, `lk.loot`, automap on); war cries every 75 s; MP < 15 % ends the
run. Fixes on the way: automap style "tunnel" (lines H16-23 S75-122 V65-120; tan caught the lit stone), per-style `automap_shown`
threshold (arches passed as a shown map), rejuv refill swap now only for `needs_rejuvs` tasks (Meph): it had turned tunnels into LK.
White non-supply picks now save `fixtures/raw/pick_white_*` frames: **check them for Archon Plate labels.**
Not done: Act 2 spawn shortcut (games end in AT -> next spawns in Lut Gholein -> A2 WP -> A3 -> A3 WP -> Lost City, ~2 min);
skipped because gems are picked nearly every run, so stow (Act 3 stash) is due anyway. Option: stow only when the inventory is
getting full, then A2 WP -> Lost City directly.

**2026-11-13 10:45: Ancient Tunnels entrance: found by the bot itself, and the learned route works (2/3 live).** Stephen: armors
(Archon Plate etc.) are next most important; sockets always by cube recipe, never Larzuk (memory). New: `config ui.wp_lost_city`
(Act II tab, 6th entry, verified) + `town.WP_TAB`; `durance` now area-agnostic: red automap style (`use_style`, Lost City sand is
the tan color), edge-matched area names (`area_is`, templates area_lost_city / area_ancient_tunnels), scan grid in `SCAN`,
`pre_scan`/`rescan`/`toward` options, junk labels skipped (`is_junk`), precise warps (hop close, find the label by its text image:
box widths vary 108-216 px), re-click after a door opens. `tools/find_tunnels.py` found the **Trap Door at world (-4952, -2978)**
NW of the WP (~15 search games, ~6 deaths/chickens; evading after a struck scan + war cries + merc made it survivable).
`bot/tunnels.py:to_tunnels` (WP -> door -> inside) and `tools/goto_tunnels.py`. Inside: tan dungeon automap like Durance.
Gotcha: never kill a live tool with plain `timeout` (left her standing in the Lost City twice): `timeout -s INT` so finally saves & exits.
**Next:** the tunnels part: explore AT with the stop-graph explorer (tan), Blizzard packs, Alt-scan and pick white/gray bases
(filter already shows normal + socketed Archon Plate, Monarch, etc.), save & exit; then a `tunnels` Task. Merc revive failed once
"not enough gold?" (deaths cost gold): watch. Supervisor is stopped (F12 08:34); LK resumes when it restarts.

**2026-11-13: KVM gone; Stephen reaches GLaDOS remotely.** His xrdp login made its own X server (:10) and dropped the seat0 session, so `:0` sat at the greeter: no D2R, uinput ACL went to lightdm. Fix (docs/glados.md "Remote access"): `tools/glados_remote_setup.sh` (sudo, Stephen runs once) = LightDM auto-login + x11vnc on :0; autostart starts the supervisor at login (new single-instance lock). Stephen says Battle.net login worked 11-12, so the 11-12 hang below is presumed over: verify in the first session log. MF swap still pending.

**2026-11-12 18:45: BLOCKED: Battle.net hangs on "Logging in" after GLaDOS rebooted (~17:30).** 3 tries (18:18 supervisor, 18:31, 18:34; each a clean kill + relaunch): the Login window spins and its log stops after "Fetched new tact metadata" (catalog 5260; 11-11's good start went on to CatalogLoader and a token-security-checkpoint challenge). Network and Blizzard version endpoints answer fine. Supervisor is up (pid 5557) on `lk` and retries with backoff; if it never gets in, Stephen has to look at the Battle.net window (possible sign-in prompt: not for the bot). `tools/stash_probe.py enter` now launches D2R itself.
- 19:50 digging: the client never opens a connection to us.actual.battle.net:1119 (TCP from GLaDOS works); log goes silent after "Maintenance update requested". Trigger: Battle.net Agent auto-updated 2.41.2.9852 -> 2.42.0.9873 at 18:18 exactly when failures began (it re-downloads 9873 if moved aside). Proton unchanged since 11-10. Moved aside (reversible, in AppData/Local/Battle.net.aside-20261112 and ProgramData/Battle.net/Agent.aside-20261112): the catalog Cache (catalog loads now, login still hangs); CachedData.db put back (has login_cache). Not tried (may sign Stephen out, his call): moving BrowserCaches aside, logging out/in via the gear icon.
- **MF swap (Stephen asked, one-off, waiting on the launcher):** back to the 247 % set of 11-11 19:25 (backup 20261111-192526). Personal tab: Shako (2,0) -> helm, Kira's back there; Oculus (1,0) -> orb slot (screen right, weapon set II), the orb back there; Gheed's GC (4,0) -> inventory. Shared page 1: Chance Guards (0,0) -> gloves, Magefist back there. Shared page 3: Nagelring 30 % (0,7) -> d2s RightRing = screen-left ring (983, 316), Dwarf Star back there. Stash grid: cell (0,0) at ~(36, 87), pitch 37.8. Do it with stash_probe, a screenshot after each click; check MF in the next session's log. Then LK still (Stephen: LK for now).
- **Ancient Tunnels (Archon Plate for Enigma), Stephen OK'd building it offline/later:** needs Act II WP tab -> Lost City, the tunnel entrance route (discoverable, Nightmare-proof), a pack-clearing loop (new), white "Archon Plate" label reading. Note: Hell AT bases get 4 os from Larzuk; 3os natural (gray, already picked) or the cube socket recipe.

**2026-11-12: chest template fallback.** When the hover scan gets no chest tooltip, `open_chest` looks for the closed chest sprite (16 hand-labeled templates in `bot/assets/templates/chest/`, score >= 0.9 within 150 px of the expected point) and clicks it. Replayed over all 668 past `chest_not_found` frames: a chest found in 324 (49 %), agrees with all 34 hand labels (no hits on the 10 no-chest frames). Logs "chest by template"; a closed chest still at the clicked point afterwards saves `chest_template_unopened`. Takes effect next session. Next: count both in the logs; the tooltip miss itself is still unexplained.

**2026-11-11 23:20: detector labeling (perception plan, part 1).** Live hook (`DetSaver` in bot/recorder.py, `recording.det_daily_cap` 300/class/day): full frame + where the bot *proved* a chest (tooltip hit, frame from before the hover; and the opened chest after), a bonfire (anchor), the town / LK waypoint (template) -> `fixtures/raw/det/`. Starts with the next session. Hand labels in `fixtures/det/labels.jsonl` (`tools/det_label.py`): 34 `chest_not_found` frames boxed by eye (16 chests, 39 monsters); `tools/det_propose.py` template-matches those 16 chests: leave-one-out visible chests 0.89-1.00, no-chest frames <= 0.87; 323 proposals >= 0.9 reviewed (sheets: all chests) and accepted -> 311 frames, 339 chests. `tools/det_dataset.py` -> `datasets/det_v1` (gitignored, YOLO, chest only: the flame-blob bonfire rule boxed the gold orb over the characters, fire-enchanted monsters and sparks; `--bonfire` waits for reviewed labels). **Train only with the bot stopped** (1050 has 2 GB, D2R holds 1.9). **Finding: west_nw / east_nw miss 11-12 % of chest visits (others 1-5 %), and in 14 of 34 failure frames the chest is plainly visible ~(+19, +29) px from the expected point, where scan ring 1 hovers right over it, yet no chest tooltip was accepted.** Not position. The 11-08 tooltip-text bug is fixed (old rejected crops pass now). Next: D2R_DEBUG_TOOLTIPS on one session to see what the hover shows there; or a template fallback (score >= 0.9 near the point -> click it).

**2026-11-11 19:35: Current gear on the Bot tab, MF gate fixed, tray launch fixed.** `bot/gear.py` totals res (Hell, Anya), absorbs, MF/GF, FCR/FHR breakpoints, skills, attributes; `armory/build.py` adds it as `gear` (subprocess, so the running supervisor picks it up), `gen.py` adds `sl` (slot). MF gate now counts socketed runes (read 192 % vs real 247 %, wrongly skipped Meph at 19:18). Linux launch no longer waits for a Battle.net window when it's already running in the tray (19:18 start failed). Plan checkboxes: owner-only (server-checked login), ticks were always per-browser. **MF setup costs resists: cold 28 %, light/poison 73 %, no fire absorb** (Kira's + Dwarf Star out).

**2026-11-11 19:15: D2R closed after every normal session end.** After ~12 h it held 3 GB RAM and 1.95 of 2 GB VRAM and play slowed. Supervisor calls `bot.io.close_game()` (Linux: SIGTERM, the close button is ignored; Windows: taskkill, untested) after "ended normally" only, not F12 / Stop / mouse trip; the next session relaunches it. Supervisor restarted 19:16 (pid 39139).

**2026-11-11 19:00: magic find gate.** Meph ran days at 0 % MF (Shako + Oculus sat in her stash): the reason drops fell off. Stephen has two setups, ~0 % (cows, bases) and ~280 % (Meph). `bot/mf.py` reads MF from the session-start backup via d2dump (equipped minus weapon swap, plus inventory charms); `mf.min: {meph: 200}` swaps Meph for LK when below, Bot page shows MF and a red warning. d2dump is a Linux build: Singularity reads None, so no gate there. Auto gear swapping not built (Stephen chose detect only).

**2026-11-11 18:25: gray labels picked (7ddb635).** Socketed/ethereal runeword bases (Stephen farming an Archon Plate for Enigma; runes are enough via cube: Vex->Ohm->Lo->Sur->Ber->Jah). New `gray` kind in `loot.pick`; range is a guess (no live sample). **Check the first `fixtures/raw/pick_gray_*.png`** and narrow it; watch for clicks on non-items. Session restarted 18:25 to load it.

**2026-11-11 08:15: learned-perception plan started** (Claude Doc "D2R Bot: Learned Perception Plan",
https://claude.ai/artifact/Jcv2cgA9F1z1cnNH4FDs1V): detector first, danger predictor second, no RL. Stephen OK'd a
separate training env (`d2r-train`: torch cu126 + ultralytics + onnx) and Claude doing the labeling. Recorders live
(bot/recorder.py, config `recording:`): fixtures/raw/sampled (640x360 every 10 s out of town) and fixtures/raw/danger
(5 s windows on chicken/death/30-pt drop/random calm). Next: auto-label from logged successes, hand-label failure
frames, train detector v1, gate on chest_not_found frames. Meph loot check: 124 empty-loot frames show only gold
labels: nothing missed; Dracul's Grasp (uvg) is on two show rules; installed filter == repo. Meph paused for the rejuv
refill (Stephen: keep the rule).
Training env `d2r-train` installed (torch 2.14 cu126 sees the GTX 1050), but D2R holds ~1.9 of its 2 GB: train only
while the bot is stopped (or on Singularity: RTX 4060 laptop GPU). Site (bdd8c1a): Bot is the first + default tab of
/bot/, tabs styled as buttons; no hash = Bot, so the console polls for any visitor (~4 DO rows per 15 s each, fine).

**2026-11-11 07:25: mouse trips fixed (20211e9).** 02:05 a "mouse moved by user" trip with nobody at GLaDOS quit
mid-LK (no save & exit: she died there) and the supervisor read it as F12, so nothing ran all night. Earlier unexplained
trips: 11-09 20:44, 11-10 12:28. Now: XInput2 raw motion names the device that moved; a jump with no physical
input is logged ("cursor jumped with no physical pointer input") and ignored. A real one trips with the device name, then
the bot saves & exits and the supervisor restarts after 10 quiet min. F12 unchanged. Check: which device shows up in
trips, and whether the game-start stale-cursor jump (78, 264) is now ignored and harmless. Windows: no watcher yet.

**Site (2026-11-10 16:15): convergentblue.com/bot/ is one page: armory tabs (Plan, Chronicle, Stash, Cube) + a Bot tab
(console, loot log; polls only while open). /armory/ is gone (Stephen). Unlisted (noindex, no sitemap).**
- /bot/: public to watch; Start/Stop greyed out until "Owner sign-in" (DASH_TOKEN). worker/bot.js, Durable Object
  `BotState`. Free plan: DO rows read 5M/day; v1 blew it 2026-11-10 (table scan per check-in), fixed 7c5f5d9 (~4 rows
  per request). DO calls blocked until 00:00 UTC 11-11 (7 pm ET 11-10).
- Armory data: Stephen's armory_tools (from Drive) are in `armory/`; `bot/armory.py` rebuilds from the newest
  `backups/<ts>/` (never the live saves) and uploads gzipped pagedata.json to /api/bot/armory. The supervisor runs it
  every 5 min when a new backup exists, but the running supervisor (pid 34686, started 11-09) predates the hook:
  restart it between sessions. Until then / until the DO reset, a background loop retries `python -m bot.armory` every
  10 min (logs/armory_retry.log). Page template = convergentblue src/pages/bot/index.astro (first ported by
  armory/to_site.py); edit goals there.
- Open checks (11-10 11:00): (1) after 7 pm ET, /bot/ shows live armory data and the Bot tab/owner sign-in work (the retry loop lives in the
  Claude session that started it; if that session is gone, run `python -m bot.armory` once by hand). (2) Next cube
  session saves fixtures/raw/cube_{runes,gems}_last.png: compare reads to armory/pagedata.json (rune 11 fix 6884e2b;
  Flawless Skull read 13 vs plan 3, maybe the same tens-digit miss on gems). (3) 11-10 09:31 the stale-cursor trip
  happened on a fresh D2R; closing D2R (`wmctrl -c "Diablo II: Resurrected"`) and restarting fixed it. Root cause open.
- 11-10 16:00: the armory tabs fall back to public/bot/snapshot.json (saves of 11-10 12:41) when the API is down; it is a
  hand-copied file in the site repo (refresh: cp armory/work/pagedata.json there, commit, push). Item meta shows ilvl.
- 11-10: two deaths (02:16 LK fire pack 64%->0 in 1.2 s; 07:45 Meph, belt empty, merc dead, 92%->0 in 3 s) were logged
  "fail: could not open the esc menu"; save_and_exit now clears the death screen first (63f552b). Live-untested.
- Node 22: conda env `node22`. Site pushes: Stephen allowed `git -C /data/AutoDev/convergentblue push origin main`.
  Later: local `bot/web` through desired.json; systemd --user unit (ask).

**2026-11-09 15:00: every session stopped at game start ("mouse moved by user", same spot)** after Stephen used
GLaDOS by hand: D2R's in-game cursor was stale, the weapon-set check's inventory toggle warped from it. Restarting
D2R fixed it (docs/glados.md). Cube: Amn 54 waiting on Chipped Amethyst (5); rune recipes now use their gems down to
0 (`cube.gem_keep`), 40 Amn still wait for gem drops.

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
