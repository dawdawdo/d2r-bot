---
name: machines-and-target
description: "Singularity (Windows) is the dev/test box for the D2R bot; GLaDOS (Linux Mint) is the eventual run target, ignore it for now"
metadata:
  node_type: memory
  type: project
  originSessionId: 4505bf4f-0217-4c27-b5fa-f04a1901ad81
  modified: 2026-10-25T18:16:03.825Z
---

- **Singularity**: brand-new Windows 11, 1920×1080 @ 100% DPI. All bot building and testing happens here. D2R installed at `C:\Program Files (x86)\Diablo II Resurrected`.
- **GLaDOS**: separate Linux Mint machine; Stephen wants the bot to eventually run there (hence the `bot/io/` backend split). Stephen said (2026-10-25) to ignore it for now, so the CLAUDE.md "not running on GLaDOS" check doesn't need asking about.

**Why:** Stephen clarified this after I asked about the Syncthing/GLaDOS rule.
**How to apply:** don't block on GLaDOS questions; keep platform code inside `bot/io/` so a Linux backend works later. See [[stephen-autonomy-prefs]].

**2026-11-05 update:** Stephen wants GLaDOS to run the bot while he's using Singularity, taking turns. He ruled out running both at once as too dangerous, so no separate-character plan. Duriel comes first; GLaDOS not started. Still unknown: whether D2R is installed there, and whether the game's pixels match the Windows templates.
