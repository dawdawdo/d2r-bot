# Progress

**Current milestone:** M1 (perception). Offline work done; **waiting for Stephen to say
he's done with the machine** before any live game.

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
