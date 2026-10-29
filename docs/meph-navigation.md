# Mephisto runs: getting from the Durance 2 waypoint to the Level 3 stairs

Route: town -> WP Durance of Hate Level 2 -> **stairs to Level 3** -> Mephisto (Level 3 is a preset map: the
moat spot is at a fixed offset from its entrance) -> kill -> loot -> (red portal to Act 4) -> save & exit.

Blizzaga's map is fixed, so Level 2's layout is fixed too: the stairs are at one place relative to the WP.
The hard part is the same as LK's M4: find that place once, then get there reliably every run.

## What 2026-10-27 showed (live, ~15 Durance games)
- Waypoint, buffs, arrival: work (`town_to_wp` / `act4_to` with `wp_durance_2`).
- The dungeon is dark and the character's light circle moves with her: the LK odometer measured
  "didn't move". A high-pass + local-contrast odometer (`Odometer(dungeon=True)`) fixes single hops
  (test: true (0, -211) measured exactly), and grid exploration then covered ~150 stops.
- But positions still drift and jump over many hops: two thumbnails of the *same* spot (WP in view) were
  labelled 550 px apart. Durance also repeats identical room tiles, so "looks the same" isn't proof of
  "is the same place". A global map from odometry isn't reliable here.
- No stairs seen yet in the explored part (~ x -2000..+2400, y -800..+1000 px around the WP).

## Options
1. **Teach once, then repeat (recommended).** Stephen plays one trip himself: WP -> Level 3 stairs,
   teleporting as usual, while `tools/record_route.py` (to build) saves every right-click and the view
   after it. The bot then replays the clicks from the WP and, after each hop, compares the view with the
   recorded one; the phase-correlation offset between the two corrects the next click (local, no global
   map, so no drift). Teleport-when-struck jumps are caught the same way (view doesn't match -> look up the
   nearest recorded view). ~5 minutes of Stephen's time; the rest I build and test unattended.
2. **Bot finds the stairs itself.** Explore as a tree of click sequences from the WP (deterministic
   landings from the fixed arrival spot), recognise revisits by view matching, and hover-scan for the
   "Durance of Hate Level 3" tooltip. No help needed, but likely many hours of live exploration with
   deaths along the way, and fragile against the repeated tiles.
3. **Skip Durance 2.** Not possible: Level 3 has no waypoint.

Either way the runtime part (teach-and-repeat with view matching) is the same; only who does the first trip
differs. Level 3 (moat trick, Static Field + Frozen Orb, kill detection, loot, red portal) comes after.

## 2026-10-29: route taught (option 1 after all)
Stephen played the trip once (`tools/record_route.py`). He held the right button, so only 2 right-clicks
were logged for ~10 teleports; the stairs view still placed on the search canvas at **(5804, 631)** world
(east of the WP, resp 0.46 from every guess). The search had stood 140 px from there (stop 79) without
seeing the stairs tooltip. Also: the Level 2 area-name template matches Level 3 at 0.955 (one digit
differs), so `durance_level` compares both templates.

Replay (`durance.to_level3`, live test `tools/goto_level3.py`): stop-graph path WP -> stop 79 with the
automap fix, go to the stand spot, line up on the recorded stairs view (`view_offset`), click, confirm
Level 3. Recorder TODO: log button releases and sample the cursor while a button is held.
