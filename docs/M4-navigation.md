# M4 — Finding the super-chest huts

## Key fact
Single-player keeps the map seed in `Blizzaga.map`, so **Lower Kurast has the same layout
every game** (Stephen confirmed the seed already has good super-chest huts). The only
per-game variation is monsters, and small landing jitter from teleport.

## Options

### A. Scripted teleport route (recommended start)
Record, once, the sequence of teleport clicks (screen offsets from the character, who is
always at screen center) from the LK waypoint to each hut and between huts. Replay it each run.
- + Simple, fast (each hop is about 0.3 s), easy to debug from logs.
- − Teleport lands near the clicked spot, not exactly on it, and the error adds up over
  ~10 hops; a monster or wall can shift a landing.
- Mitigation → checkpoints (B-lite): after every few hops, check the minimap or an on-screen
  landmark against a stored template and correct with one extra hop.

### B. Minimap localization
Stitch a reference image of LK from minimap captures (Tab overlay). Each tick, match the
live minimap against it to get the player's map coordinates, then teleport toward the
target hut's map coordinates.
- + Robust to drift; recovers from any position.
- − More work (stitching, overlay/background noise, scale calibration). Probably needed later
  for the Linux port anyway, since window sizes may differ.

### C. Explore and detect huts on screen
Detect hut roofs/chests with templates while exploring.
- − Slow, fragile; it ignores the fixed-seed advantage. Not recommended.

## Plan
Build **A with minimap checkpoints**: the route is a list of hops; checkpoints carry a
minimap template plus the expected offset; on mismatch, do a corrective hop or abort the run
(save & exit). If checkpoints turn out flaky, grow them into B.

Route recording tool (`tools/record_route.py`, to build): I teleport manually once while
the tool logs click offsets and saves minimap crops at chosen checkpoints.
