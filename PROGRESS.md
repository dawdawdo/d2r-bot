# Progress

**Current milestone:** M4 (find the chest huts). **M1, M2 and M3 done 2026-10-25.** M2: 20/20 live
cycles (7.4 s). M3: 13/13 town → WP → Lower Kurast (about 22 s per full cycle). Stephen gave
the go-ahead to run live (approved remotely); PowerShell commands are pre-approved.

**M3 facts:** the town waypoint is east of the temple: a round platform with two blue braziers.
The vertical blue ring near Ormus and the white ground circle are decoration. The route is
in config `town.route`. D2R needs a hover before a click to interact (DirectInput.click
does this). Opening a side panel shifts the camera and cursor by 240 px (the user-mouse
guard allows exactly that). The automap is set to Full Screen with no transparency; the area name shows
top-right only while it's open. `python -m bot.run --mode lk`.

**Live facts (2026-10-25):** `D2R.exe` launches directly (no Battle.net). It opens with the
intro → title "Press any key" → main menu (Offline tab, Blizzaga selected). Window client
1280×720 (it moves around; coordinates are client-relative). Show Items = **Toggle** (Alt toggles).
Automap = Mini Map Right, starts closed. Life orb text on. The A3 town is Kurast Docks.
Loot filter `LK Bot` is active, all 5 rules load (see docs/loot.md for gotchas).
Tools: `tools/peek.py`, `tools/act.py` (scripted inputs + capture), `tools/state_check.py`,
`tools/orb_probe.py`. `python -m bot.run --runs N` recovers to the main menu from any state.

**Works (offline, 26 tests pass, fixture tests skip until frames exist):**
- M0: `bot/io/` boundary (Windows backend + fakes), F12 kill switch, `GuardedInput`
  (also trips the kill switch if a human moves the mouse), save backup, logging,
  `tools/capture.py`. Repo: github.com/dawdawdo/d2r-bot (private).
- Launcher: `open_backend(..., launch_exe=...)` starts `D2R.exe` directly if its window isn't up
  (untested: does it run without Battle.net?).
- M1 detectors (`bot/vision/`): orbs, label colors, template screen classifier, loading.
  All regions/thresholds in `config.yaml`, **uncalibrated**. Tools: thumbs, label, crop_template.
- M2 scaffold: controller (foreground-only input, timeouts, failure frames), lifecycle,
  `python -m bot.run --runs N` → `runs.csv`. Simulated 20/20.
- Docs: `docs/M4-navigation.md` (approved: scripted route + minimap checkpoints),
  `docs/loot.md` (native loot filter draft `filters/LK Bot.fltr`), `docs/roadmap.md`
  (map-change detection → relearn → map hunting; Linux; remote control).

**Loot filter:** `LK Bot.fltr` copied into the save folder 2026-10-25 (approved; backup
`backups/20261025-145937` taken first). Stephen approved adding any filters needed. Still to do:
select it in-game and verify it hides/shows as intended.

**Next step (live):** launch D2R → set windowed 1280×720 + low graphics in-game (approved)
→ capture frames → calibrate → fixture tests green → commit M1 → live M2 ×20.

**Decisions made (2026-10-25):** bot launches the game itself; in-game video changes OK;
M4 plan A OK, but map relearning is required eventually; loot = Dol+ runes + unique rings
(+ optional cube gems).

**Open questions for Stephen:**
- Remote start channel: recommended = Claude Remote Control (see last chat message).
- I can't run `/usage` myself; tell me if weekly usage nears 85%.
