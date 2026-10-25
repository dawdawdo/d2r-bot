# Progress

**Current milestone:** M0 done → M1 (perception) blocked on live frames.

**Works:**
- conda env `d2r` has deps (pinned in `requirements.txt`); `pytest` → 8 passing.
- `bot/io/` boundary: `Window`/`Capture`/`Input`/`HotkeyListener` ABCs; Windows backend
  (user32 + mss + pydirectinput + pynput); fakes for offline tests. A test enforces that no
  platform imports exist outside `bot/io/`. All coords are client-relative.
- `KillSwitch` (F12) + `GuardedInput` (every input action checks it; key-ups always allowed).
- `bot/session.py`: logging → `logs/`, arms F12, backs up saves → `backups/<ts>/`.
- `tools/capture.py --label <state>`: F9 snaps a frame to `fixtures/raw/`, `--interval` for
  continuous capture, F12 quits. Read-only, sends no input.

**Broken / unknown:** window title/size/hotkeys still unverified (D2R not running).

**Next step:** M1 needs ~50 real frames. Needs Stephen to launch D2R (windowed 1280×720)
or OK me launching it, then capture each state with `tools/capture.py`.

**Open questions for Stephen:**
- Is **Blizzaga** the Sorc? (Most recently modified .d2s; set in `config.yaml`.)
- Confirm D2R is *not* running on GLaDOS before I touch the game here.
- OK for me to launch D2R and drive menus for frame capture, or will you capture frames?
- Loot filter: what's worth picking up? (Default: runes, uniques, sets.)
- Sorc build/gear: enough to survive Hell LK if something goes wrong?
- I can't run `/usage` myself — please tell me if weekly usage is near 85%.
