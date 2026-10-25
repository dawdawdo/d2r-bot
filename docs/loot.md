# Loot (M5)

## What Stephen wants
- Runes **Dol (r14) and up**.
- Unique rings (SoJ chance).
- Optional: gems used to cube Dol+ upward (he probably already has them; off by default).

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
- Super-chest hut #1 has a **Locked Chest**: opening it uses a key from inventory. Keys run out;
  restocking (buy from a vendor) needs handling eventually.

Still to verify with real drops: that show rules override earlier hide rules.

Original status: draft. Category and item codes still need checking in-game: whether the
"hide all gear" rule is accepted, and that low runes, potions and gold are hidden. The file
must sit in the save folder to be selectable, which needs Stephen's OK to add (it's a new
file there; no save files are touched).

## Cube gems for Dol+ upgrades (D2R recipes)
| Upgrade | Gem |
|---|---|
| Dol→Hel | chipped emerald (gcg) |
| Hel→Io | chipped diamond (gcw) |
| Io→Lum / Lum→Ko / Ko→Fal / Fal→Lem / Lem→Pul / Pul→Um | flawed topaz/amethyst/sapphire/ruby/emerald/diamond (gfy gfv gfb gfr gfg gfw) |
| Um→Mal … Ohm→Lo | topaz/amethyst/sapphire/ruby/emerald/diamond (gsy gsv gsb gsr gsg gsw) |
| Lo→Sur … Cham→Zod | flawless topaz/amethyst/sapphire/ruby/emerald (gly gzv glb glr glg) |
