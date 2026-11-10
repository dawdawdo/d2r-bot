# Armory tools

Rebuilds "Blizzaga's Armory" (claude.ai artifact https://claude.ai/artifact/9cuUKVRf8ew3tpnpPfrk9q,
local copy `D:\Google_Drive\Projects\D2R_Bot_20260314\Blizzaga's Armory.html`) from the D2R saves.

## Update (one command)
Needs both folders connected to the Claude session: `D:\Google_Drive\Projects\D2R_Bot_20260314`
and `C:\Users\steph\Saved Games\Diablo II Resurrected`. Then, in device_bash:

    bash "$HOME/mnt/D2R_Bot_20260314/Codebase/armory_tools/update.sh"

It backs up the saves to `Codebase/backups/<timestamp>/`, dumps every `.d2s` and the shared stash with
`d2dump`, runs inv.py -> gen.py -> chron.py -> build.py, saves `pagedata.json`, writes `built_<ts>.html`,
and overwrites the root copy. Exit 2 + `NEED_SAVES` means the saves folder isn't connected.
To refresh the published artifact: stage the root copy and publish it to the artifact URL.

## Pieces
- `scanbundle.tgz`: Linux `d2dump` (Rust, crate d2s 0.1.1, save v105) + `txt105/` base tables + `xl/` 3.0 game
  tables (github.com/pinkufairy/D2R-Excel). Source for d2dump is in `d2dump/`.
- `inv.py` saves -> inventory.json (every `saves/<Name>.json`, so new characters are picked up automatically).
- `gen.py` -> pagedata.json: items with readable stat lines, runes, gems, materials, characters, `snap`
  (latest in-game save time). Keeps `rwdb` and `farm` text from the previous pagedata.json.
- `chron.py` decodes the Chronicle section of the .d2i (format notes in the project handoff doc);
  adds missing uniques grouped by slot (`mug`) and missing set items by set (`msg`).
- `build.py` merges the Chronicle, works out what changed since the previous snapshot (`delta`: new items,
  Chronicle finds, rune changes; only recomputed when the saves changed) and fills `armory.html`.
- `armory.html` is the page template (style + markup + script; `__DATA__` placeholder).
  Goals, farm guides, wanted runewords and move/ditch rules live in its script (`GOALS`, `FARMS`, `WANT`,
  `MOVES`, `DITCH`). Older templates: `template2*.html` + `style.css` (pre-Nov 5 redesign).
- `cube.py` regenerates cube recipe HTML from cubemain.txt (static tables are baked into armory.html).

## On GLaDOS (since 2026-11-10)
The page now lives at https://convergentblue.com/bot/ (convergentblue repo, `src/pages/bot/index.astro`, merged with the bot console 2026-11-10, ported
once by `to_site.py`; edit GOALS/FARMS/WANT/MOVES/DITCH there, not in `armory.html`). Data comes from
`/api/bot/armory`. The bot supervisor runs `bot/armory.py` whenever a session start leaves a new save backup in
`backups/`: same pipeline as `update.sh`, in `armory/work/`, reading only the backup copy; it uploads the gzipped
`pagedata.json` when it changed. By hand: `python -m bot.armory [--force] [--no-upload]`.
