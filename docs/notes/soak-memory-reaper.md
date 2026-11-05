---
name: soak-memory-reaper
description: Long D2R bot soaks in background shells get killed by Claude Code under memory pressure; run them in the foreground in short batches
metadata:
  node_type: memory
  type: project
  originSessionId: 2d8f6117-d906-4f2d-880e-32271c479772
  modified: 2026-11-03T03:37:56.154Z
---

On 2026-10-26, Claude Code killed two background soak runs (`python -m bot.run --runs 10`) for "system low on memory", both times before or at D2R launch. Singularity has 16 GB; idle apps hold most of it: a vmmem VM (~4 GB, probably the Claude desktop sandbox), ChatGPT (~1.9 GB), Steam (~1.4 GB). D2R uses ~3 GB and does not leak. Stephen said he'll close Steam and ChatGPT before future sessions.

**Why:** the reaper only targets background shells while the session is idle.
**How to apply:** launch D2R detached (`Start-Process`), then run soaks in the foreground, about 3 runs per command (each run ~2 min; 10-min tool limit). Related: [[stephen-autonomy-prefs]].

Update 2026-11-02: Meph runs take ~3.5 min, so 3 runs blew the 10-min limit -> moved to background -> reaped.
Use `--runs 2 --max-minutes 4` for Meph. **If a reap happens anyway, don't stop and wait: fall back to LK runs**
(Stephen: "still just fall back to LK runs, because we know those work"). That overrides the reap notice's
"don't restart" for bot runs. See [[stuck-fallback-lk]].

Update 2026-10-27: use `--max-minutes 8` with `--runs 20` so a batch ends at the menu before the 10-min tool
timeout (a `timeout 595` kill once landed mid-run; ensure_main_menu recovered it).
