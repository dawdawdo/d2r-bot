# Progress

**Current milestone:** M4/M5 (chests + loot) working for **1 chest**; needs more huts. M1–M3 done.

**Works (2026-10-25, live):**
- `python -m bot.run --runs N --mode chests`: launch/recover → Hell game → corpse pickup at spawn →
  (heal at Ormus + fresh game if HP < 70%) → town route → WP → Lower Kurast (area-name check)
  → map fingerprint → teleport route (`maps/blizzaga_hell/route.yaml`) → open chest (hover-scan
  finds it despite landing jitter) → Alt labels → pick rune/unique labels → save & exit. About 30 s per run.
  Logs `runs.csv` (result, chests, picked). Stops on `map_changed` (route stale).
- Guardian (controller): on every observe/click/sleep while out of town: potion < 70% (skips empty
  belt slots), chicken < 50%, death detection. Only reads HP on frames classified in-game.
- Modes: `lifecycle` (M2, 20/20), `lk` (M3, 13/13), `chests` (M4/M5, last 8 runs ok).
- Tools: `goto_lk.py`, `explore.py` (teleport + stitch + fires + hover-scan + actions; always ends
  with save & exit), `npc_probe.py`, `hover_scan.py`, `peek.py`, `act.py`, `state_check.py`.

**Broken / risks:**
- Only one chest (hut1, a Locked Chest SW of the WP: uses keys from inventory, which run out).
- Monsters (Hell Buzzards) sometimes attack in hut1; the bot never fights. Two deaths so far, while
  developing (both corpses recovered).
- Potions: belt row has 3 rejuvs left (slot 1 empty). Ormus heals for free; potion restock not built.
- Ormus is sometimes not found (wanders); the run continues anyway.

**Next step:** find more super-chest huts (waiting on Stephen's answer; else keep scouting with
`explore.py`), add them to route.yaml; then M6 (stuck detection, timeout, 50-run soak).

**Open questions for Stephen:**
- Where are the super-chest huts relative to the LK waypoint?
- Blizzaga's skill hotkeys? (Which key is Teleport / Blizzard / Frozen Armor.) The bot could cast
  an armor or kill buzzards instead of only fleeing.
- Keys and potions: OK to buy keys and potions from vendors automatically later?
- I can't run `/usage` myself; tell me if weekly usage nears 85%.

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
The A3 town WP is east of the temple (platform with two blue braziers). Show Items = toggle (Alt).
Automap Full Screen, no transparency. Skills on Q W E R A S D F; Teleport = right-click.
The game keeps .fltr files in memory and overwrites them; install filters only while D2R is closed.
`LK Bot.fltr` repo version adds "Hide gems" (not yet installed; needs a game restart).
