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
- Traveling to Act 2 changes the act new games start in: always return to A3 before exiting.

## Map change detection and relearning (requested by Stephen)
The LK route is only valid for the current map seed (`Blizzaga.map`), which will eventually
be replaced, probably by accident.
1. **Detect** (build with M4): store a *map fingerprint*, minimap crops at the LK waypoint and
   at the first checkpoint. If arrival doesn't match the fingerprint, mark the route stale,
   stop runs and notify Stephen instead of teleporting blind.
2. **Relearn** (later): explore LK from the waypoint (teleport frontier exploration, stitching
   the minimap as it goes, i.e. M4 option B), detect super-chest huts on screen, then build a new
   route (a list of hops plus checkpoints) and fingerprint automatically.
3. **Map hunting** (end goal): create game → score the LK layout (number of huts, distance from
   the waypoint) → if bad, reroll the map → repeat until good → relearn → resume runs.
   Rerolling the seed must be done through the game itself, never by editing save files.

Routes are stored as data per map (`maps/<fingerprint-id>/route.yaml`), never hard-coded.

## Linux backend for GLaDOS
Implement `bot/io/linux.py` (evdev/uinput input, X11/Wayland capture). Coordinates are
client-relative already.

## Remote control
Stephen starts and stops sessions remotely (see PROGRESS for the chosen channel); the bot
sends a push notification on finish, fatal error, or map change.
