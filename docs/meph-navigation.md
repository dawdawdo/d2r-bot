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

## 2026-10-29 night: stairs work live; Level 3 mapped roughly
**Stairs (done).** The stand spot was where Stephen's *second* hold started (cursor at (984, 257)), not where
he clicked the stairs. From the stand spot one teleport toward (984, 257) puts her on top of the dais
against the arch, and hovering (636, 251) shows **"To The Durance of Hate Level 3"**. That label is drawn
*below* the cursor on a dark box touching dark scenery, so the object-tooltip detector never saw it (that
is also why the search found no exits at all). `vision.tooltip.find_label` diffs a parked-cursor frame
against the hover frame instead. Live: 10.3 s WP -> Level 3, every game the town walk worked (8/8).
The recorder now samples while the right button is held (`teach.HOLD_EVERY`).

**Level 3 (probe tool `tools/probe_level3.py`, frames in `maps/blizzaga_hell/durance3_auto/probe/`).**
Fresh-canvas automap odometry is useless here (few lines yet); fixed hop sequences from the arrival are
repeatable instead (same landing every game so far).
- Arrival -> 6 x teleport (-350, -60): the **dock** at the east edge of the blood moat. The red portal
  (Hellgate) is visible across the moat to the left (it's there before the kill).
- Dock -> (-430, +50): onto the **portal side**, next to the portal. Quiet: 20 s standing, HP steady.
- Portal side -> (-300, -150): onto a round mosaic platform; **Mephisto** (boss bar "Mephisto / Demon")
  comes from the upper left and *reaches her*: the portal side is his side, not an island.
- Moat trick works from the dock: aggro him from the platform, teleport back (300, 150) then (430, -50):
  he stops at the far moat edge, ~(-400, -120) px from her, and stays there.
- **But she can't hold the dock**: his lightning reaches her there, and Council members (Wyand Voidbringer:
  Mana Burn, Fire Enchanted; hydras) stand on the dock. Energy Shield goes from full to broken in ~3-5 s
  every time (5 tries, all chickens, no death). Blizzards at his spot: MP was already 0.
- Ormus heals now also require MP >= 60% (an ES that broke last game leaves her at MP 0) and HP >= 95%
  (belt empty: life carries over), with 2 Ormus tries.

**Decisions for Stephen (Level 3):**
1. Record his own Meph kill once: `python tools/record_route.py --level 3` (bot takes her down the stairs,
   then hands over; F10 when done). Shows the real moat spot and how he deals with the Council.
2. `/players` for Meph games: 7 makes Meph (and the Council) much tankier; lower = faster kill, worse drops.
3. Potions: the belt is empty and the policy is chest rejuvs only. Meph without potions is chicken-only.

**Stephen's recorded kill (2026-10-30 22:26, `maps/blizzaga_hell/durance3_route/`, /players 7 likely).**
Blizzard (`d` on right-click; the recorder logs clicks, not hotkeys) from across the water. 104 s, no deaths.
What he did differently from the probe: **he cleared the way first.** Long Blizzard stands on packs at
three spots between the stairs and the moat (9-38 s, 41-52 s, 57-81 s on the timeline; the Council), then
teleported in (odometry lost for 5 hops), stood at ~(985, -31) on the route canvas and blizzarded Mephisto
across the water (cursor up-right of her, ~(1020, 65) screen; boss bar "Mephisto / Demon" at step 120).
MP ran to empty several times: he waited for mana between volleys. Then (1040, -82), more Blizzard,
"The corruption begins to fade" = dead, red portal right by her, clicked it -> Pandemonium Fortress.

**Plan for the bot's Meph task (from the recording):**
1. `to_level3` (works). Load the route canvas as the Level 3 odometer (better than a fresh one).
2. Replay his stops in order (positions where the view moved), `Walker.go` per stop, no scans.
3. At each of his Blizzard stands: cast Blizzard at his recorded screen points until no monster name
   shows on a hover sweep, waiting for MP >= 40% between volleys; danger rules as in LK
   (ES broken -> drink/flee to the previous stop; life < 50% -> chicken).
4. At the moat stand: Blizzard at his point until "The corruption begins to fade" (or the red portal
   label) shows. Then take the portal (ends in A4, as the act4 exit does). Loot across the water: later.

**Correction from Stephen (2026-10-30 evening):** he did NOT clear the Council. First Blizzards: Mephisto
came to the arrival area and his merc tanked. He teleported to keep the merc between them; after the merc
died he finished Mephisto with the moat trick (lower bank, Meph stuck at the far edge up-right of her).
"The corruption begins to fade" / "tremors" chat lines are Terror Zone notices: unrelated, ignore them.
Potions may be bought for Meph runs. Loot: whatever passes the filter.

**Live 2026-10-30 23:05-23:08 (/players 7):**
- AutoMapFade had flipped 1 -> 2 ("Automap Opacity: Custom" 50%): lines nearly invisible, every probe
  stopped with "automap won't show". Likely the bot's own `/players 7` chat line typed into the game
  instead of the chat box (players_set.png shows no confirmation). Set back via Options -> Gameplay ->
  Automap Opacity = Center (Settings.json AutoMapFade 1). TODO: `chat()` must confirm the chat box
  opened before typing.
- Dock (6 x (-350, -60)) reached again; the frame matches Stephen's view 84.
- Moat trick from the probe sequence (-430,50) (-300,-150) w1 (300,150) (430,-50): the return hops did
  NOT cross back; she ended on Mephisto's side and chickened (life 325 -> 312/635 with Meph + hydras on
  her). Bot HP read lagged (87% shown while the orb said 51%).
- Conclusion: fixed hop sequences are not repeatable enough here. Next approach: teach-and-repeat
  against Stephen's recorded views (view_offset resp 0.5-0.8 between close frames), and a fresh look at
  the HP read in Durance lighting.

**Live 2026-11-01 17:24-17:54 (/players 1, Stephen's choice; ~10 probes, `tools/probe_level3.py`):**
- /players 1 is a big change: standing on the dock 10 s cost no life (at 7 the shield broke in 3-5 s).
- **Return across the moat by view works**: `R` remembers the dock frame, `D` teleports back using
  `view_offset` against it (3-4 hops, ends 7-50 px off; resp 0.12-0.3 on the dock). Fixed return hops did not.
- **Name bar** (`bot/vision/namebar.py`, template `name_mephisto.png`): box at the top centre, red as far as
  the hovered monster's life goes. Mephisto vs Bremm / Council Member / Blood Lord told apart; his life
  tracked 0.96 -> 0.15 over Stephen's first kill. Live hover works (Wyand Voidbringer seen).
- **Blocker: Wyand Voidbringer** (Council, always Mana Burn + Teleportation; other mods random per game)
  stands up-right of the dock and reaches her within ~10 s, with fire hydras beside her. Mana Burn empties
  mana = no shield, no teleport, no Blizzard; then life falls to the 50% chicken. 4 of 4 dock fights lost
  this way, also with 8 pre-emptive Blizzards at his approach (800, 160) and the shield chicken off (`--es-hp 0`).
- Her belt was empty all session (no potions to answer the burn). Her "teleport when struck" gear throws
  her off the dock when hit; the kill loop re-checks the spot before waiting for mana.
- Not seen yet: whether Blizzards from the dock reach Mephisto (never got that far with mana left).

**Live 2026-11-01 17:58-18:24 (Stephen chose C: mana potions + his safe spot):**
- `buy_mana_at_ormus` (bot/town.py): Ormus -> Trade (opens on Misc) -> shift+right-click his best mana potion
  (395, 376) until the 4 belt slots show potions. Works live. `to_durance2(buy_mana=True)` also revives a dead
  merc at Asheara first. With mana potions the guard must not drink on low life (`potion_hp_pct` 0): it
  emptied 16 potions at 67% life once.
- **Stephen's safe spot** = his view 206 (`L206` in the probe), ~(-800, +230) world px from the dock. Path:
  dock -> 2 x (-364, +105) -> match view 206 (resp 0.32-0.41, ends < 10 px off). Wyand never reached her
  there; 2+ minutes at 100% when Mephisto was asleep.
- **Waking him is unreliable**: dock -> his platform (-430,50) (-300,-150), wait, back (view match; fallback
  now reverses the hops since R) -> safe spot. He came 2 of 5 times. Blizzards at his platform from the safe
  spot didn't wake him.
- **When he comes**: he stands at the moat edge, top centre from the spot ((640-720, 20) on screen); the
  name-bar search finds him and Blizzard there takes him 100% -> 29% in ~12 s, 100% -> 62% in one round.
- **But his lightning reaches the spot**: one burst 520 -> 42 life in < 2 s (no chicken in between; the
  "orb empty" check got her out). Hit and run (3 casts, teleport (120, 260) away, 1.5 s, back by view) still
  chickened at 43% (merc was dead then). Stephen had his merc alive in the recording.

**Next (bot side):** retry with the merc alive (revive now automatic) and hit-and-run; if his lightning
still lands, try 2 casts per volley and a longer retreat; make the wake reliable (longer platform stay, or
cast at him on the platform before leaving).
