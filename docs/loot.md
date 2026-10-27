# Loot (M5)

## What Stephen wants
- Runes **Dol (r14) and up**.
- Unique rings (SoJ chance).
- Optional: gems used to cube Dol+ upward (he probably already has them; off by default).

## What the filter shows (checked 2026-10-27: repo file = installed copy in Saved Games)
| Rule | Items |
|---|---|
| Show Dol and higher runes | r14 Dol, r15 Hel, r16 Io, r17 Lum, r18 Ko, r19 Fal, r20 Lem, r21 Pul, r22 Um, r23 Mal, r24 Ist, r25 Gul, r26 Vex, r27 Ohm, r28 Lo, r29 Sur, r30 Ber, r31 Jah, r32 Cham, r33 Zod (all 20) |
| Show unique rings | any unique ring (SoJ, BK, Nagel, Manald, Raven Frost, Dwarf Star, Wisp…) |
| Show rejuvenation potions and keys | rvs, rvl, key (picked only when the belt / key stack needs them) |
| Hidden | all gear, El–Amn (r01–r13), gold, potions, scrolls, ammo, gems, skulls |

Picked items are stashed by the stowaway at the stash stop; stashed runes are logged by name in
`logs/loot.csv` (tracked in git), item tooltips in `logs/loot/` (local).

## Approach: let D2R's native loot filter decide
D2R loot filters (`*.fltr`, JSON rules, later rules override earlier) hide items, labels
included. With `filters/LK Bot.fltr` active, Alt shows labels **only** for wanted items, so
the bot picks up every visible label. No OCR or reading of label text needed. As a second
check, pickup only clicks labels whose color is rune-orange or unique-gold (or white, for
gems if enabled).

**Verified 2026-10-25:** installed and selected in-game; all 5 rules load (gem rule off).
Gotchas learned:
- Rule **names must not contain `+`**: the game silently drops the whole rule.
- The game loads `.fltr` files **only at startup** and keeps them in memory; switching
  profiles or editing in the UI **writes its cached copy over the file**. Install filter files
  only while D2R is closed.
- Select a filter: Esc → Loot Filter (640,420) → profile dropdown (558,108).

- Real drop seen 2026-10-25: gold ("967 Gold") still shows (`gld` doesn't hide it) and gems
  showed because no rule hid them; a "Hide gems" rule was added (installed at the next game restart).
- Locked Chests use a key. Keys come from chest drops (picked while the stack is low) and from Hratli
  when the stack reads below 3 (`town.count_keys` / `buy_keys`, verified by the stack tooltip).

Verified with real drops (2026-10-27): show rules override the earlier hide rules (Dol–Ohm runes shown).

Original status: draft. Category and item codes still need checking in-game: whether the
"hide all gear" rule is accepted, and that low runes, potions and gold are hidden. The file
must sit in the save folder to be selectable, which needs Stephen's OK to add (it's a new
file there; no save files are touched).

## Cube gems for Dol+ upgrades (D2R recipes; reference only, the gem rule is off)
| Upgrade | Gem |
|---|---|
| Dol→Hel | chipped emerald (gcg) |
| Hel→Io | chipped diamond (gcw) |
| Io→Lum / Lum→Ko / Ko→Fal / Fal→Lem / Lem→Pul / Pul→Um | flawed topaz/amethyst/sapphire/ruby/emerald/diamond (gfy gfv gfb gfr gfg gfw) |
| Um→Mal … Ohm→Lo | topaz/amethyst/sapphire/ruby/emerald/diamond (gsy gsv gsb gsr gsg gsw) |
| Lo→Sur … Cham→Zod | flawless topaz/amethyst/sapphire/ruby/emerald (gly gzv glb glr glg) |
