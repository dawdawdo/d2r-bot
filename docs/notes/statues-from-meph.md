---
name: statues-from-meph
description: "Ancients' statues drop from non-terrorized Mephisto; Stephen wants them kept, they count toward his ancients progress"
metadata:
  node_type: memory
  type: project
  originSessionId: 1633dcb5-1abd-47da-b433-9dc24c7396fe
  modified: 2026-11-05T00:24:19.156Z
---

2026-11-04: Stephen saw many statues collected by earlier bot Meph runs. He says this confirms they drop from non-terrorized bosses, and they help his progress towards the ancients.

**Why:** they're wanted loot that no filter rule names, so a future tightening could lose them by accident.

**How to apply:** keep statues when changing the filter or `loot()`. Today they get through because no hide rule covers them and boss drops use `take_all`. See [[targeted-loot-plan]], [[meph-only-until-back]].
