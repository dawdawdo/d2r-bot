# Running the bot on GLaDOS

GLaDOS (Linux Mint 22.3, X11, D2R under Proton) runs the bot while Stephen uses Singularity. **Taking turns only; he has ruled out running both.**
D2R must also stay closed on Singularity, on every character: they share the stash file, and Syncthing syncs the saves both ways within minutes.

**Status (2026-11-08): the Linux backend works live** (`bot/io/linux.py`). `--mode lifecycle` passes. Not yet run on Linux: LK, Meph, cubing, the recorder.

## GLaDOS facts (2026-11-08)
- Python: Miniconda at `/data/AutoDev/miniconda3` (`/data` is root-owned). Env `d2r`: `/data/AutoDev/miniconda3/envs/d2r/bin/python`.
- D2R under Proton Experimental, in the prefix of the Steam shortcut **3949906016 = Battle.net launcher** (saved login).
  The game files live on the SSD at `~/Games/Diablo II Resurrected`. `/data/steam/games/Diablo II Resurrected` is a symlink to them
  (the HDD copy `...hdd-backup` can be deleted once Stephen is happy). On the HDD, loads took 30 s-2 min and froze the desktop.
- Saves: `~/.steam/debian-installation/steamapps/compatdata/3949906016/pfx/drive_c/users/steamuser/Saved Games/Diablo II Resurrected`.
  This is the folder Syncthing syncs. It's set per platform in `config.yaml` (`paths.save_dir.linux`), so no config.local.yaml is needed.
- Launch (`launch_game`): `steam steam://rungameid/<appid<<32|0x02000000>` starts Battle.net. Then `proton run Battle.net.exe
  --exec="launch OSI"` in the same prefix (sometimes ignored right after an update, so it's retried after 60 s). About 95 s cold.
- Input: kernel uinput via python-evdev, a keyboard plus an absolute pointer spanning the X screen. `/dev/uinput` is writable through a uaccess ACL.
  `tools/uinput_selftest.py` checks the mapping (0 px).
- Window: Wine draws into a child X window inset 2 px. `client_rect` uses that child. The WM maximizes a screen-sized window,
  so `launch_game` un-maximizes it. D2R options were set to Windowed 1280x720 (Settings.json is in the synced save folder!).
- Colors: D2R's Brightness slider (Settings "GammaHD") at max, 3200, makes raw frames match the Windows fixtures, so no
  capture gamma (`game.capture_gamma.linux` 1.0). A capture-side gamma 0.70 was tried first: it lifted tooltip boxes along
  with the shadows, and LK chest tooltips stopped being found.
  Templates with scenery behind text can drop below threshold: add a `<template>_mask.png` (`tools/make_mask.py`).
- **Settings.json is NOT synced** (it's in the save folder's `.stignore`): each machine has its own game options. GLaDOS needed
  **Large Font Mode on** (Settings "Low Vision Mode" 1). Without it every panel (inventory, stash, waypoint) is ~15% smaller
  and shifted, so all panel coordinates miss. `bot.run` now stops if it's off. Also set on GLaDOS: Windowed 1280x720, Show Items Toggle.
- **Lag (2026-11-08):** hover -> tooltip on screen: VSync on median 105 ms (max 222, std 27); **VSync off 84 ms (max 109,
  std 10)**, so VSync is off on GLaDOS. ~60 fps, GPU not the limit. Remaining extra lag is handled by `game.input_lag`
  (0.05 s after moves/before clicks) and `game.frame_lag` (0.08 s added to teleport settles). Not tried yet: capping the
  frame queue (NVIDIA/vkd3d env vars in the Battle.net shortcut's Steam launch options; ask Stephen first).
- Captures: 17 ms a frame (mss bytes via np.frombuffer + cv2). np.asarray(ScreenShot) took 52 ms and caused stalls.
- Started through Battle.net, D2R opens character select on the **Online** tab; `select_character` clicks Offline (`ui.offline_tab`).
- The first session with a fresh `logs/state.json` cubes right away (every 6 h): 171 transmutes, about 14 min, no per-step log lines.
- RAM: 15 GB with an 8 GB swapfile (added 2026-11-08). Close the Claude desktop app (its VM uses about 1.5 GB) and browsers for long runs.

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
