# Roadmap beyond phase 1

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
