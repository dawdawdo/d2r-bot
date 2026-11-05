---
name: stephen-teleport-style
description: Stephen teleports by holding right-click (repeat cast), so a recorder that logs only presses misses most hops
metadata:
  type: user
---

When Stephen plays a route for the bot (tools/record_route.py, 2026-10-29), he holds the right mouse button and
steers; D2R repeats Teleport. Only 2 presses were logged for ~10 teleports (~5800 px).

**Why:** the press-only recorder made the route look like 2 short hops; positions had to come from the automap canvas.
**How to apply:** for any future teaching recording, sample cursor and view while a button is held (or derive the
path from automap fixes), and don't let the bot's save & exit run while he may still touch the mouse
(the kill switch trips). Related: [[stephen-autonomy-prefs]].
