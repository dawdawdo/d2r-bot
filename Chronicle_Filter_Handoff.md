# Handoff: Chronicle-only loot filter for the LK bot (Nov 4 2026)

## Goal
Change the bot's loot filter so it only shows/picks up uniques and set items that are **not yet in Stephen's Chronicle**, and make the filter **regenerable** (a script), because the missing list shrinks as items are found.

## Key constraints
- Unidentified uniques/sets only show their **base name** on the ground. The pixel bot can't tell which unique it is, so filter by **base item code + rarity** (unique / set). Some bases are shared by several uniques: over-inclusion is fine.
- Keep existing pickups regardless of the Chronicle
- Also update the bot's own pickup logic in `config.yaml` if it filters separately from the in-game filter.

## Where the Chronicle lives (decoded)
- Last `55 AA 55 AA` section of `ModernSharedStashSoftCoreV2.d2i` (section type 2). Scan for the magic `c0 ed ea c0` rather than hardcoding offsets.
- After the magic: u16 version (1), then counts (u16 104, u16 203, u16 5), then zero padding; records start 24 bytes after the magic.
- Record = 10 bytes little-endian: `u16 tag (unknown, maybe finder hash) | u32 minutes since 1970 | u32 id`.
- Order: **103 set records** (id = `*ID` in setitems.txt), **203 unique records** (id = `*ID` in uniqueitems.txt), **5 runeword records** (id = save-file runeword_id), then a (0, t, 0) trailer. Treat the header counts with care: 103/203/5 is what validated against the game tables. Re-check the split if counts change: set ids are <= 139, unique ids <= 437, runeword ids >= 20000.
- "Eligible" = `disableChronicle` blank and `spawnable` = 1 → 403 uniques, 135 set items. Skip the 5 quest items (Staff of Kings, Horadric Staff, Hell Forge Hammer, KhalimFlail, SuperKhalimFlail).
- Game tables (3.0): `D:\Google_Drive\Projects\D2R_Bot_20260314\Codebase\armory_tools\scanbundle.tgz` → `xl/uniqueitems.txt`, `xl/setitems.txt` (column `code` / `item` = base code).
- Human-readable missing list: `D:\Google_Drive\Projects\D2R_Bot_20260314\Chronicle_Missing_20261104.txt`.

## .fltr format
JSON; see the existing `LK Bot.fltr`. Rules have `ruleType` (show/hide), `equipmentRarity`, `itemCategory`, `itemCode`. Keep the existing "hide all gear" rule and add show rules with `itemCode` lists for each rarity; match the existing schema exactly and check rule-order precedence in-game on one test item.

## Snapshot of base codes to show (as of Nov 4; regenerate, don't hardcode)
- Unique (164 codes): `6hx 6l7 6lw 6rx 6ws 7b7 7bk 7bl 7br 7cr 7cs 7fl 7ga 7gd 7gi 7gl 7gm 7gw 7ha 7kr 7ls 7lw 7m7 7p7 7pa 7s7 7sb 7sc 7sr 7ta 7ts 7wa 7wc 7wh 7ws 8cb 8cs 8l8 8lb 8lw 8mx 8rx 8sw 8ws 92a 9ax 9b9 9ba 9bt 9dg 9gd 9gi 9gm 9gs 9gw 9m9 9ma 9mp 9mt 9p9 9qs 9sc 9sr 9tw 9vo 9wc 9wn 9ws 9yw am7 am9 amb amd amf amu bac bad bae bar bsd bsh buc ci2 ci3 clb cm1 cm2 cm3 cst dgr drb dre fla flb ghm gsc hax hla jew lbw lea lgl lst mac nef obf pa9 pac pae pax qui rin sbw scp sml spc ssd sst uar uh9 uhb uhg uhm uit ulc uld ulm umg uml upk urn utb utc uts utu uui uul uvb uvc uvg vip wac wae waf wnd wst xar xcl xhb xhl xhm xlm xmb xml xow xsk xtb xtg xts ywn zhb zmb ztb zvb`
- Set (31 codes): `6cs 7gd 7qr 7wd 7ws aar amu ba5 cap ci3 ful gsc lbl lbt lea lgl lrg ne9 paf qui sml uar uh9 uhm ult uth uul vbt xmg xml ztb`

## Deliverables
1. `tools/chronicle_filter.py`: reads the .d2i + tables, prints the missing list, writes `LK Bot.fltr` (backup of the old .fltr first) and updates `config.yaml`.
2. Tests on a fixture copy of the .d2i (counts 103/203/5 for the Nov 4 file).
3. PROGRESS.md note + commit. Rerun the script after each bot session.
