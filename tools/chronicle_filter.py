"""Regenerate the Chronicle part of the loot filter: show only uniques and sets the Chronicle doesn't have yet.

  python tools/chronicle_filter.py              # print the missing list, write filters/LK Bot.fltr
  python tools/chronicle_filter.py --dry-run    # print only
  python tools/chronicle_filter.py --install    # also install it (refused while D2R runs: see install_filter.py)

Rerun after a bot session; a stale filter only shows a few too many items. The save folder is only read here.

Unidentified items show their base name, so the rules go by base code + rarity. Bases shared by several
uniques show them all. All other rules in the file stay as they are, except the two fixed in `build_filter`.

Rule semantics (docs/loot.md): within a rule the equipment* fields AND together and the item* fields are a
separate alternative: rarity + `itemCode` shows every item of that rarity. So gear codes go in `equipmentItemCode`.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MAGIC = bytes.fromhex("c0edeac0")
RECORD = 10
MAX_SET_ID, MAX_UNIQUE_ID, MIN_RUNEWORD_ID = 139, 437, 20000
QUEST = {"Staff of Kings", "Horadric Staff", "Hell Forge Hammer", "KhalimFlail", "SuperKhalimFlail"}

# Codes with a filter category we've seen work: shown by category instead of by equipmentItemCode.
CATEGORY_OF = {"rin": "rings", "amu": "amule"}
# Not gear: jewels and charms have their own any-rarity item rules; the bot only picks the colors it wants.
ITEM_RULE_CODES = {"jew", "cm1", "cm2", "cm3"}

GEMS = [f"g{grade}{color}" for grade in "cfs" for color in "vybgrw"] + ["skc", "skf", "sku"]

RULE_UNIQUES = "Show Chronicle missing uniques"
RULE_SETS = "Show Chronicle missing sets"
RULE_AMULETS = "Show unique amulets"
RULE_SET_CATEGORIES = "Show Chronicle missing set jewelry"
RULE_JEWELS = "Show jewels"
RULE_GEMS = "Show all other gems"
GENERATED = {RULE_UNIQUES, RULE_SETS, RULE_AMULETS, RULE_SET_CATEGORIES, RULE_JEWELS, RULE_GEMS}


@dataclass
class Chronicle:
    sets: set[int]
    uniques: set[int]
    runewords: set[int]


def parse_chronicle(data: bytes) -> Chronicle:
    """Read the Chronicle section of a shared stash .d2i. Raises ValueError if the layout isn't the known one."""
    at = data.rfind(MAGIC)
    if at < 0:
        raise ValueError("no Chronicle section in this file")
    version, head_sets, n_uniques, n_runewords = struct.unpack_from("<4H", data, at + 4)
    if version != 1:
        raise ValueError(f"unknown Chronicle version {version}")
    n_sets = head_sets - 1  # the header's first count includes the (0, t, 0) trailer (checked against the tables)
    total = n_sets + n_uniques + n_runewords
    start = at + 24
    if start + (total + 1) * RECORD > len(data):
        raise ValueError(f"Chronicle section too short for {total} records")
    ids = [struct.unpack_from("<HII", data, start + i * RECORD)[2] for i in range(total + 1)]
    sets, uniques, runewords = ids[:n_sets], ids[n_sets : n_sets + n_uniques], ids[n_sets + n_uniques : total]
    if (max(sets, default=0) > MAX_SET_ID or max(uniques, default=0) > MAX_UNIQUE_ID
            or min(runewords, default=MIN_RUNEWORD_ID) < MIN_RUNEWORD_ID or ids[total] != 0):
        raise ValueError(f"Chronicle split looks wrong: {n_sets}/{n_uniques}/{n_runewords}; recheck the format")
    return Chronicle(set(sets), set(uniques), set(runewords))


def load_tables(path: Path) -> tuple[list[dict], list[dict]]:
    """(uniqueitems, setitems) from scanbundle.tgz (read in place, nothing unpacked) or a folder holding the two."""
    def read(name: str) -> str:
        if path.is_dir():
            return (path / name).read_text(encoding="latin-1")
        with tarfile.open(path) as t:
            member = next(m for m in t.getmembers() if m.name.endswith(f"/{name}"))
            return t.extractfile(member).read().decode("latin-1")

    def rows(name: str) -> list[dict]:
        return list(csv.DictReader(io.StringIO(read(name)), delimiter="\t"))

    return rows("uniqueitems.txt"), rows("setitems.txt")


def eligible(rows: list[dict]) -> list[dict]:
    """Items the Chronicle can list, minus the quest items. The game's own total counts those too (403 uniques here)."""
    return [r for r in rows if r.get("spawnable") == "1" and not r.get("disableChronicle")
            and r["*ID"].strip() and r["index"] not in QUEST]  # blank id: the "Expansion" divider row


def missing(uniques: list[dict], sets: list[dict], chron: Chronicle) -> tuple[list[dict], list[dict]]:
    return ([r for r in eligible(uniques) if int(r["*ID"]) not in chron.uniques],
            [r for r in eligible(sets) if int(r["*ID"]) not in chron.sets])


def _show(name: str, **fields) -> dict:
    return {"name": name, "enabled": True, "ruleType": "show", "filterEtherealSocketed": False, **fields}


def _code_rule(name: str, rarity: str, codes: set[str]) -> list[dict]:
    gear = codes - ITEM_RULE_CODES - set(CATEGORY_OF)
    return [_show(name, equipmentRarity=[rarity], equipmentItemCode=sorted(gear))] if gear else []


def build_filter(old: dict, unique_codes: set[str], set_codes: set[str]) -> dict:
    """The filter with its generated rules replaced and the two rarity + itemCode rules fixed. Others are untouched."""
    stray = set_codes & ITEM_RULE_CODES
    if stray:
        raise ValueError(f"missing set items on non-gear bases, no rule for them: {sorted(stray)}")
    rules = [dict(r) for r in old["rules"] if r["name"] not in GENERATED]
    for r in rules:  # rarity + itemCode showed every unique and set
        if r["name"] == "Show BiS uniques":
            r.pop("itemCode", None)
            r["equipmentItemCode"] = ["ulc", "usk", "uvg"]  # amu, jew, cm3: own rules below / Show charms
        elif r["name"] == "Show Tal Rasha Lidless Eye":
            r.pop("itemCode", None)
            r["equipmentItemCode"] = ["oba"]
    new = [_show(RULE_JEWELS, itemCode=["jew"]),  # Rainbow Facet; a jewel may not count as gear
           _show(RULE_AMULETS, equipmentRarity=["unique"], equipmentCategory=["amule"])]  # Mara's, Highlord's, Atma's
    if cats := sorted(CATEGORY_OF[c] for c in set_codes & set(CATEGORY_OF)):
        new.append(_show(RULE_SET_CATEGORIES, equipmentRarity=["set"], equipmentCategory=cats))
    new += _code_rule(RULE_UNIQUES, "unique", unique_codes) + _code_rule(RULE_SETS, "set", set_codes)
    new.append(_show(RULE_GEMS, itemCode=GEMS))
    at = next(i for i, r in enumerate(rules) if r["name"] == "Show Pul and higher runes")
    return {**old, "rules": rules[:at] + new + rules[at:]}


def main() -> int:
    from bot.config import load_config

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--stash", type=Path)
    ap.add_argument("--tables", type=Path)
    args = ap.parse_args()
    cfg = load_config()
    stash = args.stash or Path(os.path.expandvars(cfg["paths"]["save_dir"])) / "ModernSharedStashSoftCoreV2.d2i"
    chron = parse_chronicle(stash.read_bytes())
    uniques, sets = load_tables(args.tables or Path(cfg["loot"]["chronicle_tables"]))
    miss_u, miss_s = missing(uniques, sets, chron)
    print(f"Chronicle: uniques {len(chron.uniques)}/{len(eligible(uniques))}, "
          f"sets {len(chron.sets)}/{len(eligible(sets))}, runewords {len(chron.runewords)}")
    print(f"\n== missing sets ({len(miss_s)}) ==")
    for r in miss_s:
        print(f"  {r['index']} [{r['item']}]")
    print(f"\n== missing uniques ({len(miss_u)}) ==")
    for r in miss_u:
        print(f"  {r['index']} [{r['code']}]")
    unique_codes, set_codes = {r["code"] for r in miss_u}, {r["item"] for r in miss_s}
    print(f"\nbase codes: {len(unique_codes)} unique, {len(set_codes)} set")
    if args.dry_run:
        return 0
    src = ROOT / "filters" / f"{cfg['loot']['filter_name']}.fltr"
    bak = ROOT / "backups" / f"filter-repo-{time.strftime('%Y%m%d-%H%M%S')}"
    bak.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, bak / src.name)
    new = build_filter(json.loads(src.read_text(encoding="utf-8-sig")), unique_codes, set_codes)
    src.write_text(json.dumps(new, indent=4) + "\n", encoding="utf-8")
    print(f"wrote {src} (old copy in {bak})")
    if args.install:
        return subprocess.call([sys.executable, str(ROOT / "tools" / "install_filter.py")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
