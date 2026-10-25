# Progress

**Current milestone:** M1 (perception). Offline work done; waiting on live frames
(Stephen is using the PC; no live game until he says so).

**Works (offline, 25 tests pass, fixture tests skip until frames exist):**
- M0: `bot/io/` boundary (Windows backend + fakes), F12 kill switch + `GuardedInput`,
  save backup, logging, `tools/capture.py`. Repo: github.com/dawdawdo/d2r-bot (private).
- M1 detectors (`bot/vision/`): orb fill % (HSV rows), item labels by text color
  (unique/rune/set; rune vs unique split by saturation), template screen classifier +
  black-frame loading detector. All thresholds/regions in `config.yaml`, **uncalibrated**.
- M1 tools: `tools/thumbs.py` (downscaled contact sheets / grid crops, cheap to view),
  `tools/label.py` (raw → `fixtures/labeled/<state>/` + expected-values json),
  `tools/crop_template.py` (→ `bot/assets/templates/` + config snippet).
  `tests/test_vision_fixtures.py` checks every labeled frame automatically.
- M2 scaffold: `bot/controller.py` (wait_for with timeout + failure-frame dump; refuses
  input unless D2R is foreground), `bot/lifecycle.py` (create game / save & exit),
  `python -m bot.run --runs N` → `runs.csv`. Tested against a simulated game, 20 cycles.
- M4 approach written up: `docs/M4-navigation.md` (fixed seed → scripted route + minimap checkpoints).

**Broken / unknown:** window title, UI click points, orb regions, label colors all unverified.

**Next step (needs game):** capture frames per state → calibrate config → crop templates
→ fixture tests green → commit M1. Then live M2 (20 clean cycles).

**Facts:** Singularity = Win11, 1920×1080 @100% DPI. D2R at
`C:\Program Files (x86)\Diablo II Resurrected`. Char = Blizzaga (Hell map seed is fixed and good;
deaths OK). GLaDOS (Linux Mint) = future run target; ignore for now.

**Open questions for Stephen:**
- How should the game get started? Preferred: you leave D2R open at the main menu
  (Blizzaga selected, offline), windowed 1280×720. Or should I launch it myself, and does
  D2R.exe start without a Battle.net login?
- OK for me to change in-game video options (windowed 1280×720, low graphics)? The game
  stores these in `Settings.json` in the save folder.
- M4: OK with plan A (scripted route + minimap checkpoints)?
- Loot filter: runes + uniques + sets OK as default?
- I can't run `/usage` myself; tell me if weekly usage nears 85%.
