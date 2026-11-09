# D2R Armory — handoff (as of Nov 3 2026, 8:01 AM)

## Where things live
- **Armory page** (artifact): https://claude.ai/artifact/9cuUKVRf8ew3tpnpPfrk9q — tabs Goals / Farm guide / Inventory / Reference. Data snapshot: Nov 3, 8:01 AM (version 18).
- **Rebuild tools**: `Codebase\armory_tools\` (README: d2dump → inv.py → gen.py → template2.html). Game data: 3.0 tables from github.com/pinkufairy/D2R-Excel.
- Reference tab pieces already applied to template2.html (backup: template2.pre-ref.html). Wanted-runeword list = the `WANT` array in the template.
- **Save backups**: `Codebase\backups\<timestamp>\` — always back up before reading. Saves: `C:\Users\steph\Saved Games\Diablo II Resurrected` (folder access each session).
- **Every page update also overwrites** `D:\Google_Drive\Projects\D2R_Bot_20260314\Blizzaga's Armory.html` — request access to `D:\Google_Drive\Projects\D2R_Bot_20260314` (mounts as `$HOME/mnt/D2R_Bot_20260314`); only Codebase is mounted by default.

## How to rescan (worked Nov 3, cheap)
1. device_bash: back up *.d2s + *.d2i to `Codebase/backups/<ts>`.
2. `mkdir $HOME/scan; tar xzf armory_tools/scanbundle.tgz`; copy inv.py/gen.py/fmt.py + armory_tools/pagedata.json; sed inv.py line 2 to `T=S+'/txt105/'`.
3. `./d2dump c Blizzaga.d2s > saves/char.json`; other chars (Damon Malbec Myrissa Shamelock Skeld Smoked ThroatCutter) → `saves/<name>.json`; `./d2dump s ModernSharedStashSoftCoreV2.d2i > saves/stash.json`; `python3 inv.py . && python3 gen.py`.
4. Build: template2.html with `__STYLE__` ← style.css, `__DATA__` ← pagedata.json. Copy to `armory_tools/built_<date>.html`, pagedata.json back to armory_tools, and to the root copy. Update the "snapshot <date>" line (template2 holds a hardcoded date — sed it).
5. Artifact: device_stage_files on the new built_<date>.html worked (Nov 3). Then Artifact read of the URL **without path** (saves full HTML to a file; counts as viewed), and publish the staged copy to the same URL. Only the D line and snapshot date differ from the live page.

## Chronicle (decoded Nov 4)
- Stored as the **last 0x55AA55AA section of ModernSharedStashSoftCoreV2.d2i** (type 2). At section+64: magic `c0edeac0`, u16 ver=1, then counts (u16 104, u16 203, u16 5); records start at section+88, 10 bytes each: `<u16 tag (char hash?)><u32 minutes since 1970><u32 id>`.
- Order: 103 set records (setitems `*ID`), 203 unique records (uniqueitems `*ID`), 5 runeword records, then a (0,t,0) trailer. Runeword id = d2s runeword_id (CTA 20519, Infinity 20566, Insight 20568, Spirit 20635, Mosaic 27362).
- Eligible = `disableChronicle` blank and `spawnable`=1 → 403 uniques, 135 set items, 99 runewords. All recorded ids validated eligible.
- Nov 4 result: Uniques 203/403, Sets 103/135, Runewords 5/99. List: `D:\Google_Drive\Projects\D2R_Bot_20260314\Chronicle_Missing_20261104.txt` (includes owned-but-unrecorded items, e.g. found before Chronicle existed).

## Characters
- **ThroatCutter** — L93 Assassin, Mosaic martial arts. Main focus. Merc currently has Hustle (Colossus Voulge). **Infinity goes to his merc for Uber runs.** Gaps: Hell resists, empty amulet slot.
- **Blizzaga** — L91 Cold Sorc (Blizzard + Frozen Orb), Mephisto runner, MF kit. Merc (Act 2): Tal Rasha's Horadric Crest, eth Duriel's Shell, **Insight (keeping it — she needs Meditation for mana)**. Call to Arms made on a Flail (in her stash); needs 35 base Dex, she was 3 short → respec (8 Tokens of Absolution on hand).
- **Shamelock** — L68 WW Barb, Immortal King. **Smoked** — L81 FoH Paladin. **Damon** — L81 Warlock, 4/5 Horazon's.
- Mules (L1): Malbec, Myrissa, Skeld.
- Infinity (Mancatcher) currently in shared stash tab 5.

## Decisions made
- Priority: Dracul's Grasp before Hellfire Torch runs.
- ThroatCutter plan: respec Dragon Talon → Fade; Highlord's Wrath from Damon; Smoke replaces Vipermagi; all-res small charms replace Gheed's; check 75 res in Hell.
- Blizzaga respec plan (Insight merc): Str for gear, 35 Dex, 0 Energy, rest Vit. Skills: 20 Blizzard, 20 Frozen Orb, 20 Cold Mastery, 20 Ice Bolt, rest Glacial Spike; 1 each in prereqs, Teleport chain, Warmth.
- Runewords wanted: Enigma, Chains of Honor, Smoke (Infinity and Call to Arms made).
- Keep list and MF math unchanged (Ali Babas, Leoric arm, Edge, Kelpie, Gheed's on mules, Diadem, Buriza, swap uniques, Natalya's/Aldur's sets).

## Rune count (Nov 3 8:01 AM scan)
Ber 1, Sur 2, Ohm 3, Vex 3, Gul 10, Mal 5, Ist 1, Um 3, Pul 5, Lem 3, Fal 3 (plenty of low runes). Enigma: short a Jah (2 Ber + flawless sapphire).

## Endgame notes (Reign of the Warlock)
- Diablo Clone offline: sell an SoJ to a Hell vendor → Annihilus.
- Heralds drop Sunder charms. Upgrade per 3.0 cubemain: rune + perfect gem + that act's material; verify in-game.
- Colossal Ancients: five statues from terrorized act bosses in Hell; cube all five in Act 5 Hell.
- Worldstone Shards terrorize an act for the session. `/players 8` works offline.

## Charms
- Reroll: 3 perfect gems + magic charm, keeps item level.
- Skillers wanted: Martial Arts, Cold, Paladin Combat, Barbarian Combat, one Warlock tree. Pick up every magic charm the bot finds.
