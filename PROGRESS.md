# Progress

**Current milestone:** M4/M5: route has **6 chests** (5–6 per clean run). M1–M3 done. Next: M6 soak.

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

**Update 2026-10-25 evening:**
- Every run now casts Frozen Armor (q) and Energy Shield (w), and restocks the belt from the stash Materials tab
  (99 Full Rejuvs; stash is next to the town WP). Skills: q armor, w e-shield, e static, a frozen orb,
  s teleport, d blizzard, f ice blast. Inventory key = B.
- HP orb reads correctly when poisoned (green); the guardian also potions on low mana (Energy Shield drains it).
- `bot/nav.py`: odometry plus `teleport_to(world xy)`, `fight()` (frozen orb at moving blobs),
  `scan_tooltips()`. `tools/visit.py` scouts targets.
- East bonfire found at about world (1600..1900, 750..1100) relative to the LK WP, with a hut beside it.
  Heavily guarded (Hell Buzzard packs, champions): burned about 10 potions; chest not found yet.
  West bonfire at about (-2250, -450) (from the lk_west scan), not visited yet.
- **Keys: only 2 left.** Ormus doesn't sell keys; Hratli does, but I haven't found a walking route to
  his forge yet (the WP ledge is blocked by a cliff, and there's no teleport in town). Stephen: buy for
  now, eventually collect keys and rejuvs from chests (the filter already shows them).
- Can't read the weekly /usage figure; see the chat.

**Update 2026-10-25 later:**
- Keys: **24 bought from Lysander (A2)**. Route: town WP → Act II tab → Lut Gholein; Lysander's stall is
  south-east of the WP; Trade, shift+right-click the key = buy a stack. Must return to A3 via the WP before exiting
  (new games start in the act you exited from). Hratli's forge was not reachable on foot (automap marker
  in the east ruin, but he wasn't there).
- `bot/vision/tooltip.py`: shape-based tooltip detection (dark box + text). Robust to moving NPCs.
- West bonfire is at about world (-2250, -380) from the LK WP; hut to its NW; Doom Ape champion pack there.
- Goal recorded: portable Python app (Windows + Linux). Keys target = 12; runes → stash Materials tab.

**Session end 2026-10-25 ~20:33 (Stephen pressed F12; he needed the PC). Game may be left mid-run.**
- Route now has 3 huts (hut1 SW near the WP, hut3 east bonfire, hut2 west bonfire), with world-coord targets
  via odometry. Best runs: **3 chests per run** (20:20-20:22). Chest search reads tooltip text
  (tt_chest*.png templates) so Armor Stands are skipped.
- **Stephen: each bonfire has THREE super chests** (I only open one per hut). Next: scan each bonfire
  hut fully (tools/visit.py), record all chest world coords, add them to route.yaml.
- Late runs often missed the hut2/hut3 chests (search started 70+ px off): odometry drift after
  fighting/potions. Fix idea: re-anchor on the bonfire (fire blob) before searching for chests.
- One more death (champion Doom Ape pack at hut3, 20:23). Added: guardian check on every chest-scan
  point and an energy-shield-broken chicken (MP < 8% and HP < 75%). Gold was lost on death; corpse picked up at the next spawn.
- `hot_movers` skip rule disabled: the motion detector counts orb shards/torches. Needs a real
  monster detector.
- One "unique" pick was a false positive (nothing new in the inventory). Valuable picks now save an
  evidence frame `fixtures/raw/pick_*.png`.

- **Stephen: Blizzaga has an item that casts Teleport when she's struck** → random jumps during fights.
  This likely causes the odometry "drift". Plan (agreed): keep the item; detect jumps (big shift or low
  phase-correlation response), then re-anchor on a landmark (bonfire / LK WP) before every chest
  search; if no landmark is found, go back toward the last good position, else skip the hut. Fallback:
  Stephen removes the item.

**Session 2026-10-25 23:10 → 10-26 (Stephen: "pick up where you left off"):**
- Odometry: `Odometer.lost` flags untrustworthy steps (phase-corr response < 0.04 or a step near the
  wrap limit: > 520 px across / 280 px down); `teleport_to` caps vertical hops at 220 px. `fight()`
  feeds odometry every frame. Bonfire targets re-anchor (`nav.reanchor`) before the chest search;
  corrections are usually < 15 px, and live jumps of 600 px were caught and recovered.
- Chests scouted (`tools/visit.py --bonfire=x,y` prints chest world coords): east bonfire NW hut +
  NE hut; west bonfire NW hut + NE hut; a chest W of the WP by the hollow logs. The "bonfire" by hut1
  is really the WP braziers. The east chest just E of the bonfire was seen once, then not found live:
  disabled in route.yaml. West bonfire 3rd chest: not found yet (SE hut has a closed roof; entrance unknown).
- **Big bug found:** belt restock clicked the empty slot beside the rejuv stack, so it never moved a
  potion (98 Full Rejuvs still in stash). All of today's chickens ran on an empty belt. Fixed
  (`stash.full_rejuv: [57, 250]`). The stash is now found by template (`town_stash.png`) with
  Esc+retry when Cain stands on it; walk_route re-clicks a leg if the view didn't move.
- One unique pick: evidence in `fixtures/raw/pick_unique_1025-234423.png` (not verified).

- After the potion fix, 3 clean runs in a row (5 chests each). Earlier "unique" picks were gold piles
  (label detector now requires the dark backdrop above/below the text; `tests/test_labels_real.py`).
- Per-run timeout enforced: `safety.run_timeout_s` (180 s for the LK part) -> `RunTimeout`, logged as
  `timeout` in runs.csv.
- 00:24: a 10-run soak was killed by Claude Code (system low on memory; D2R uses ~2 GB) before
  the first game started. Not restarted; waiting for Stephen.

**Next step:** M6: 50-run soak with runs.csv (re-run `python -m bot.run --runs 10 --mode chests` first). Optional: find the
west bonfire's 3rd chest and re-check the east-bonfire E chest.

**Open questions for Stephen:**
- Where are the super-chest huts relative to the LK waypoint?
- Blizzaga's skill hotkeys? (Which key is Teleport / Blizzard / Frozen Armor.) The bot could cast
  an armor or kill buzzards instead of only fleeing.
- Keys and potions: OK to buy keys and potions from vendors automatically later?
- Usage: I can't run `/usage`, but I see its output when Stephen runs it. Last reading 2026-10-25 ~19:50:
  week 23% (resets Oct 29 10pm ET), session 68% (resets Oct 25 11:10pm ET).

**Facts:** Singularity Win11 1920×1080. D2R launches directly. Window client 1280×720.
The A3 town WP is east of the temple (platform with two blue braziers). Show Items = toggle (Alt).
Automap Full Screen, no transparency. Skills on Q W E R A S D F; Teleport = right-click.
The game keeps .fltr files in memory and overwrites them; install filters only while D2R is closed.
`LK Bot.fltr` repo version adds "Hide gems" (not yet installed; needs a game restart).
