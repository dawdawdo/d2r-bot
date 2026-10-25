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

Status: **draft**. Category and item codes still need checking in-game: whether the
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
