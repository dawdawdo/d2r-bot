---
name: never-idle-outside-town
description: Never leave Blizzaga idle outside town in Hell; every tool/script must end with save & exit or stay monitored
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4505bf4f-0217-4c27-b5fa-f04a1901ad81
  modified: 2026-10-25T21:45:59.874Z
---

Every script or tool that takes Blizzaga out of town must end with save & exit (or keep watching HP with chicken logic). It must never finish and leave her standing in a hostile area.

**Why:** on 2026-10-25 `tools/explore.py` finished its hops in Lower Kurast and exited, leaving her idle. A monster killed her within about 20 s while I was reviewing the stitched map. Gear was recovered from the corpse in town; Stephen had said deaths are OK, but they cost gold and exp.
**How to apply:** default to save & exit in `finally` blocks; only skip it behind an explicit `--stay` flag; when I need to inspect something in LK, capture frames *during* the script, not after. Related: [[stephen-autonomy-prefs]].
