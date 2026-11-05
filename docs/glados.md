# Running the bot on GLaDOS

GLaDOS (Linux Mint 22.3, X11, D2R under Proton) runs the bot while Stephen uses Singularity. **Taking turns only; he has ruled out running both.**
D2R must also stay closed on Singularity, on every character: they share the stash file, and Syncthing syncs the saves both ways within minutes.

**Status: the Linux backend doesn't exist yet.** `open_backend` raises NotImplementedError on Linux. Start with LK; Mephisto and Duriel can come later.

## New session on GLaDOS
1. Copy `docs/notes/*.md` into this project's Claude memory folder. They're a snapshot of the notes from Singularity (2026-11-05). `MEMORY.md` is the index.
2. Read `CLAUDE.md`, then `PROGRESS.md`.
3. Make a Python 3.12 environment and `pip install -r requirements.txt`. `pydirectinput` is Windows-only and skipped there.
4. Write `config.local.yaml` (not in git; overrides `config.yaml`):
   ```yaml
   game:
     exe: <how D2R launches under Proton>
   paths:
     save_dir: <the save folder Proton really uses>
   ```
   Confirm Syncthing syncs that same folder.
5. `pytest` should pass without the game. Some tests may assume Windows; fix what's real.

## First job: the probe (before writing the whole backend)
Find the D2R window, capture frames at 1280x720 client size, match them against `bot/assets/templates/`, compare scores with the same screens on Windows, and try a few inputs on the character screen only. This decides how big the port is: the bot finds everything by pixels, so a different GPU or Proton may shift colors enough to need new templates.

**Ask Stephen before launching D2R or sending input, and check that Singularity's D2R is closed and the sync has settled.**

## To build
- `bot/io/linux.py`: Window, Capture, Input, hotkeys, clicks, `window_info`, `launch_game`, matching `bot/io/windows.py`. Hook it into `bot/io/__init__.py`. Candidates on X11: `mss` for capture, `pynput` or XTEST for input and listeners. Nothing outside `bot/io/` may import them.
- Check that input really reaches D2R under Proton, especially held right-click and shift-click.
- `tools/install_filter.py` `d2r_running` calls `tasklist`: move it behind `bot/io/`.
- Session backups read `save_dir`: check they find the Proton save folder.

## Switching machines
1. Stop the bot and close D2R.
2. `git push` from that machine.
3. Wait for Syncthing to settle (minutes).
4. `git pull` on the other machine, then start.

Per machine, not in git: `logs/` (including `state.json` and `loot.csv`), `runs.csv`, `backups/`, `config.local.yaml`. A fresh `logs/state.json` should be fine: keys get counted again and upkeep runs early. Check that on the first run.

`maps/blizzaga_hell/learned.json` changes during LK runs and is in git: commit it on every switch, so only one machine ever has changes.

Many Mephisto recordings (`maps/blizzaga_hell/durance3_route*/views`, `durance2`, others) are untracked on Singularity. Check what Meph needs before running it here.
