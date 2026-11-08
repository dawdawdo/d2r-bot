# D2R Bot — Lower Kurast (LK) Sorc runs

You are building this bot mostly unattended. Stephen checks in only when you are blocked
or need a decision. Read `PROGRESS.md` first every session; update it before you stop.

## Goal (phase 1)
Bot that does repeatable, *safe* LK super-chest runs with Stephen's Sorceress in
**offline single-player** D2R on this machine (Singularity, Windows, native D2R).
Proving ground only — keep it simple, then extend.

One run = main menu → create game (Hell) → Act 3 town → waypoint → Lower Kurast →
teleport to super-chest huts → open chests → pick up filtered items → save & exit. Repeat.

## Hard rules
- **Back up the character save** (`%USERPROFILE%\Saved Games\Diablo II Resurrected\`)
  to `backups/<timestamp>/` before every bot session. Never edit, delete, or write save files.
- Never run D2R/bot while it may also be running on GLaDOS (Syncthing syncs saves both ways).
  If unsure, ask.
- Global kill switch (F12) must work from M0 onward and be checked every loop tick.
- Pixels only: screen capture + image recognition + simulated input.
  No process-memory reading, no DLL injection, no game file modification.
- Keep capture/input behind `bot/io/` interfaces so a Linux backend (evdev/uinput) can be
  swapped in later. Nothing outside `bot/io/` imports pydirectinput, mss, or win32 APIs.

## Game setup assumptions (verify in M1; record actuals in `config.yaml`)
- D2R **windowed 1280×720**, fixed position, low graphics — consistent coordinates.
- Hotkeys: Teleport on right-click skill, potions on 1–4, Alt shows item labels.
- Sorc is in Act 3 with the Lower Kurast waypoint, playing Hell.

## Stack
Use the existing conda env `d2r` (Python 3.12). Do not create a venv. Install packages with
pip inside that env and record them in `requirements.txt`: `mss` (or `dxcam` if faster),
`opencv-python`, `numpy`, `pydirectinput`, `pynput` (kill switch), `pytest`, `pyyaml`.
Code goes in `bot/`, tests in `tests/`, fixtures in `fixtures/`. Starting from scratch: there is no prior code.

## Milestones (each one done = tests pass + PROGRESS.md updated + git commit)
- **M0 Skeleton**: git init; `.gitignore` (exclude `backups/`, `fixtures/raw/`,
  `fixtures/failures/`, `*.d2s`, `__pycache__/`); create private GitHub repo `d2r-bot` with
  `gh repo create d2r-bot --private --source . --push`. Push after every milestone commit.
  Then requirements, `bot/` package, config, logging,
  F12 kill switch, `tools/capture.py` (saves frames to `fixtures/raw/`).
- **M1 Perception on fixtures**: capture ~50 labeled frames (menus, char select, loading,
  town, LK, chest closed/open, low HP, dead). Detectors: screen state, HP/MP orb %,
  item labels by text color (unique, set, rune). pytest against fixtures, offline.
- **M2 Game lifecycle**: menu → create Hell game → in town → save & exit, 20× in a row clean.
- **M3 Town → LK**: walk to the Act 3 WP, open it, select Lower Kurast, confirm arrival.
- **M4 Find chests**: locate super-chest huts (minimap + on-screen templates), teleport
  there. Expect this to be the hardest part. Document the approach before you build it.
- **M5 Loot**: open chests, Alt-scan labels, pick up items that match the filter
  (`config.yaml`), skip junk.
- **M6 Safety & soak**: chicken (save & exit) at HP < 50%, potion at < 70%, death detection,
  stuck detection, per-run timeout. Then 50 unattended runs with a stats log (`runs.csv`).

## Testing strategy (also saves tokens)
- Prefer offline tests on fixtures to live play. Only go live to confirm a milestone.
- When you need to look at a frame, downscale/crop first. Don't read full-size
  screenshots in a loop.
- Save failing frames to `fixtures/failures/` with a short note for later review.

## When to stop and ask Stephen
- A decision with real tradeoffs (e.g. M4 navigation approach) once you've written up the options.
- Anything that touches saves, Battle.net login, system settings, or installs outside the venv.
- Same failure 3 times after a real fix attempt.
- Token budget: check `/usage` at session start. Stop and write a summary when weekly
  usage hits **85%** (Stephen may change this number).

## Machines
Singularity (Windows) and GLaDOS (Linux Mint, Proton) take turns running the bot, never both. Working on GLaDOS: read `docs/glados.md` first.
- **One branch: `tasks`** on both machines (`main` is fast-forwarded to it now and then; never work on `main`).
  At session start: `git checkout tasks && git pull`. Before stopping: commit (including `maps/*/learned.json`) and push.
  (2026-11-08 GLaDOS started from a stale `main` and redid work that was already on `tasks`.)
- Platform code stays in `bot/io/` (windows.py, linux.py, shared common.py). A change to one backend's interface needs
  the other one too; GLaDOS can only compile-check windows.py, and Singularity can't run linux.py, so say so in the commit.
- Per-machine values: per-platform keys in `config.yaml` (`{win32: ..., linux: ...}`) or the untracked `config.local.yaml`.

## PROGRESS.md format
Current milestone · what works · what's broken · next step · open questions for Stephen.
Keep it short: it's the "where did I leave off" page.
