# Roadmap beyond phase 1

## End goal (Stephen, 2026-10-25)
A **portable Python application** that runs on Windows or Linux. Requirements this implies:
- All OS-specific code stays in `bot/io/` (Windows backend exists; a Linux evdev/uinput + X11/PipeWire
  backend is still to do). Nothing else may import platform libraries (enforced by a test).
- Package as an installable app (`pyproject.toml`, console entry point `d2r-bot`), with config
  paths resolved per OS (save folder, game exe).

## Inventory policy
- Keys: keep exactly 12 (one stack). Today: bought from Lysander (A2). Goal: collect from chests.
- Rejuvs: belt restocked from the stash Materials tab. Goal: collect from chests.
- Runes: deposit into the shared stash **Materials** tab at the stash stop each run (to build).
- New games start in the town of the act the character was saved in. Act 2 trips must return to A3 before
  exiting. Act 4 is used on purpose: see "Act 4 shortcut" below.

## Act 4 shortcut (built 2026-10-27, Stephen's idea)
Clean LK runs end with: teleport back to the LK waypoint -> Pandemonium Fortress -> save & exit. The next
game spawns 1.6 s from the A4 waypoint (A3: ~12 s walk). Measured: exit costs ~5.8 s (teleport 2.6, menu 0.3,
load 2.5), the A4 start saves ~8 s, so a clean A4->A4 run is ~42.8 s vs ~44.6 s (median), and runs that start
in A4 but must end in LK take ~37 s. Upkeep stays in Act 3: an A4 spawn that needs the stash (runes etc.),
vendors, Ormus or the merc takes the WP to Kurast Docks and starts a fresh game; extra key stacks are dropped
at the A4 spawn. Runs that pick stash loot, need keys or a repair end in LK as before (`tasks/lk.py town_due`).
For Mephisto runs the A4 start is free: the red portal after the kill leads to A4, and the Durance 2 WP is on
the A4 WP's Act III tab. Off switch: `game.act4_exit: false`.

## Map change detection and relearning (requested by Stephen)
The LK route is only valid for the current map seed (`Blizzaga.map`), which will eventually
be replaced, probably by accident.
1. **Detect** (build with M4): store a *map fingerprint*, minimap crops at the LK waypoint and
   at the first checkpoint. If arrival doesn't match the fingerprint, mark the route stale,
   stop runs and notify Stephen instead of teleporting blind.
2. **Relearn** (built 2026-10-27, `tools/learn_map.py` + `bot/learn.py`): grid-frontier teleport
   exploration from the WP over several games (resumes from `maps/<name>/explore.json`), bonfire
   sightings from ≥ 2 grid cells, verification by chest tooltips at the 3 standard camp spots
   (`--verify`), shortest-path route + fingerprint (`--plan --write`). On Blizzaga's map it found
   both camps (within ~60 px) after ~12 games; runs on the learned route got 6/6 chests.
3. **Map hunting** (end goal): create game → score the LK layout (number of huts, distance from
   the waypoint) → if bad, reroll the map → repeat until good → relearn → resume runs.
   Rerolling the seed must be done through the game itself, never by editing save files.
   **How (researched 2026-10-27):** entering a game on another difficulty (e.g. Normal) makes D2R
   regenerate the character's maps, so Normal → exit → Hell gives a new Hell map. (The launch flag
   `-resetofflinemaps` instead gives a new map every game: useless for farming.) Consequence:
   one wrong difficulty click wipes the current map, so `lifecycle.create_game` checks the Hell
   button label before clicking. Map hunting must only run with Stephen's go-ahead.
   **Built, never run:** `tools/hunt_map.py --replaces-current-map` (reroll via a Normal game, learn with
   bot/learn.py, keep the first map with `--min-camps` verified camps, switch `logs/state.json` route).

Routes are stored as data per map (`maps/<fingerprint-id>/route.yaml`), never hard-coded.

## Linux backend for GLaDOS
Implement `bot/io/linux.py` (evdev/uinput input, X11/Wayland capture). Coordinates are
client-relative already.

## Remote control
Stephen starts and stops sessions remotely (see PROGRESS for the chosen channel); the bot
sends a push notification on finish, fatal error, or map change.
