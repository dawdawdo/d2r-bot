---
name: syncthing-and-backups
description: Saves sync between Singularity and GLaDOS via Syncthing within minutes; Singularity also has a scheduled backup keeping the last N saves per character
metadata:
  node_type: memory
  type: reference
  originSessionId: 1633dcb5-1abd-47da-b433-9dc24c7396fe
  modified: 2026-11-05T15:12:40.671Z
---

2026-11-05, Stephen: he set up Syncthing for the save files, so anything that happens on either machine reaches the other within a matter of minutes. Singularity also has a scheduled backup that keeps the last N saves for each character, as extra protection. The bot's own per-session backups in `backups/` are separate from that.

**How to apply:** when switching machines, D2R and the bot stay closed on both until the sync settles, because every character shares the stash file. Never run D2R on both at once, on any character. See [[machines-and-target]].
