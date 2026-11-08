# Progress

**GLaDOS port (2026-11-08), Linux Mint 22.3, X11. Offline only so far.**
- Miniconda is at `/data/AutoDev/miniconda3`. `/data` is root-owned and sudo needs a password, so it couldn't go in `/data/miniconda3`.
  The env `d2r` (Python 3.12.16) has every requirement except pydirectinput (Windows-only, now marked `sys_platform == "win32"`).
  Run with `/data/AutoDev/miniconda3/envs/d2r/bin/python -m pytest` (conda isn't on PATH; Stephen can `conda init` if wanted).
- Tests: **112 passed, 8 skipped**. The skips are `test_labels_real.py`, which needs `fixtures/raw/` (gitignored, not on GLaDOS).
  Fixed one failure: Linux didn't expand `%USERPROFILE%`. `paths.save_dir` is now set per platform (`win32`/`linux`),
  and `%VAR%` expands on any OS (`bot/config.py`).
- D2R on GLaDOS: a non-Steam game under Proton, installed at `/data/steam/games/Diablo II Resurrected`. Saves are in
  `~/.steam/debian-installation/steamapps/compatdata/3949906016/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected`
  (Blizzaga.d2s modified 2026-11-08 07:58, so Syncthing is live: never run on both machines at once).
- `pynput` works on X11 (xorg backend). `mss` imports fine. Not built yet: Linux input backend (`bot/io/linux.py`, evdev/uinput or xdotool).
  Not checked yet: the window size and position under Proton, and whether captured frames match the Windows fixtures.
- Next on GLaDOS: decide the input backend (uinput needs `/dev/uinput` access, which is a system setting: ask Stephen), then do a live capture
  check against the fixtures.

**Current milestone:** Phase 1 (LK) effectively done: M0–M6 met. Proposed bar for v1.0: 100+ runs untouched. Route = 6 super chests (2 bonfire camps × nw, nw_deep, ne).

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

**Broken / risks:**
- Chickens ~1 in 50 now. Teleport-when-struck jumps still cost a chest now and then.
- If Stephen rearranges his inventory, update `inventory.protected` (else his items get stashed).
- `logs/state.json` has `stash_rejuvs_empty: true`. **If Stephen puts rejuvs in the stash, delete that key.**
- Map hunting (reroll = play another difficulty, then Hell) is NOT built: it destroys the current map. Needs Stephen.

**Next step (exact):**
1. Stephen is on the PC: no live runs until he says he's off.
2. When he is: start D2R, check the new filter loads (9 rules; Esc -> Loot Filter) and that a run still picks
   runes; then the 100-run LK sign-off -> tag v1.0.
3. Next target (Stephen, 2026-10-27): **Dracul's Grasp via Hell Mephisto runs** (proposal accepted; research
   in docs/loot.md). Build `bot/tasks/meph.py` on top of branch `tasks`: A3 WP -> Durance 2 -> learned route to
   Level 3 stairs (fixed map) -> moat trick -> Static Field + Frozen Orb -> loot -> save & exit.
   Ask: LK + Meph in one game, or Meph alone? Check Blizzaga's total MF on the character screen.

**Open questions for Stephen:** Mephisto alone or combined with LK in the same game?

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
Skills: q Frozen Armor, w Energy Shield, e Static, a Frozen Orb, s Teleport (right-click), d Blizzard, f Ice Blast.
Show Items = Alt toggle. Inventory key B. Automap full screen. Asheara: NW of Ormus along the boardwalk.
Hratli: E across the plaza, SE bridge, NE bridge. Keys also at Lysander (A2). Stash next to the A3 WP.
The game keeps .fltr files in memory; install filters only while D2R is closed. Terror Zone chat notices are
orange (rune color): the chat area is in `vision.label_ignore`. Foreground soaks only (memory reaper kills background).
