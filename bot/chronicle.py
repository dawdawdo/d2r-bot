"""The Chronicle part of the loot filter: show only uniques and sets the Chronicle doesn't have yet.

Used by tools/chronicle_filter.py and the web page. The save folder is only read here, except that
installing goes through tools/install_filter.py (D2R closed, live copy backed up first).

Unidentified items show their base name, so the rules go by base code + rarity. Bases shared by several
uniques show them all. The base is the LIVE filter, so what Stephen changes in the game's editor stays: only
the rules named in GENERATED are replaced (edits to those are lost).

Rule semantics (docs/loot.md): within a rule the equipment* fields AND together and the item* fields are a
separate alternative: rarity + `itemCode` shows every item of that rarity. So gear codes go in `equipmentItemCode`.
"""
from __future__ import annotations

import csv
import io
import json
import os
import struct
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT

MAGIC = bytes.fromhex("c0edeac0")
RECORD = 10
MAX_SET_ID, MAX_UNIQUE_ID, MIN_RUNEWORD_ID = 139, 437, 20000
QUEST = {"Staff of Kings", "Horadric Staff", "Hell Forge Hammer", "KhalimFlail", "SuperKhalimFlail"}
STASH_FILE = "ModernSharedStashSoftCoreV2.d2i"

# Codes with a filter category we've seen work: shown by category instead of by equipmentItemCode.
CATEGORY_OF = {"rin": "rings", "amu": "amule"}
# Not gear: jewels and charms have their own any-rarity item rules; the bot only picks the colors it wants.
ITEM_RULE_CODES = {"jew", "cm1", "cm2", "cm3"}

RUNES = [f"r{i:02d}" for i in range(1, 34)]  # all of them, El to Zod: Stephen needs low ones for cube recipes
# Stephen's runeword bases (2026-11-06). Temporary: delete a line when he has enough, then regenerate.
RUNEWORD_BASES = {
    "7br": "Mancatcher",
    "utp": "Archon Plate",
    "uit": "Monarch",
    "9wc": "Grim Scythe",
    "7wc": "Giant Thresher",
    "ci3": "Diadem",
}

RULE_UNIQUES = "Show Chronicle missing uniques"
RULE_SETS = "Show Chronicle missing sets"
RULE_AMULETS = "Show unique amulets"
RULE_SET_CATEGORIES = "Show missing set jewelry"  # names over ~32 chars get dropped by the game
RULE_JEWELS = "Show jewels"
RULE_RUNES = "Show all runes"
RULE_BASES = "Show runeword bases"
RULE_SOCKETED_BASES = "Show socketed runeword bases"
# Removed on regenerating. Gems are back to flawless + perfect only (Stephen 2026-11-06): his own rule
# "Show flawless and perfect gems" stays, these two showed the lower grades.
OLD_NAMES = {"Show Chronicle missing set jewelry", "Show all other gems", "Show all Gems", "Show Pul and higher runes"}
GENERATED = {RULE_UNIQUES, RULE_SETS, RULE_AMULETS, RULE_SET_CATEGORIES, RULE_JEWELS, RULE_RUNES, RULE_BASES,
             RULE_SOCKETED_BASES} | OLD_NAMES


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
    """The filter with its generated rules replaced and any old rarity + itemCode rule fixed. Others are untouched."""
    stray = set_codes & ITEM_RULE_CODES
    if stray:
        raise ValueError(f"missing set items on non-gear bases, no rule for them: {sorted(stray)}")
    rules = [dict(r) for r in old["rules"] if r["name"] not in GENERATED]
    for r in rules:  # rarity + itemCode showed every unique and set
        if r["name"] == "Show BiS uniques" and "itemCode" in r:
            del r["itemCode"]
            r["equipmentItemCode"] = ["ulc", "usk", "uvg"]  # amu, jew, cm3: own rules below / Show charms
        elif r["name"] == "Show Tal Rasha Lidless Eye" and "itemCode" in r:
            del r["itemCode"]
            r["equipmentItemCode"] = ["oba"]
    new = [_show(RULE_JEWELS, itemCode=["jew"]),  # Rainbow Facet; a jewel may not count as gear
           _show(RULE_AMULETS, equipmentRarity=["unique"], equipmentCategory=["amule"])]  # Mara's, Highlord's, Atma's
    if cats := sorted(CATEGORY_OF[c] for c in set_codes & set(CATEGORY_OF)):
        new.append(_show(RULE_SET_CATEGORIES, equipmentRarity=["set"], equipmentCategory=cats))
    new += _code_rule(RULE_UNIQUES, "unique", unique_codes) + _code_rule(RULE_SETS, "set", set_codes)
    new.append(_show(RULE_RUNES, itemCode=RUNES))
    if RUNEWORD_BASES:
        # Stephen's own rule sets filterEtherealSocketed and all others here don't; what it does isn't tested, so one
        # of each: the bases show whichever way it works.
        bases = dict(equipmentRarity=["normal", "hiQuality"], equipmentItemCode=sorted(RUNEWORD_BASES))
        new += [_show(RULE_BASES, **bases), {**_show(RULE_SOCKETED_BASES, **bases), "filterEtherealSocketed": True}]
    return {**old, "rules": rules + new}


def _rule_codes(flt: dict, name: str) -> set[str]:
    return {c for r in flt["rules"] if r["name"] == name for c in r.get("equipmentItemCode", []) + r.get("itemCode", [])}


def up_to_date(flt: dict, unique_codes: set[str], set_codes: set[str]) -> bool:
    """Does this filter already show exactly what the Chronicle still needs?"""
    want = build_filter(flt, unique_codes, set_codes)
    return all(_rule_codes(flt, n) == _rule_codes(want, n)
               for n in (RULE_UNIQUES, RULE_SETS, RULE_RUNES, RULE_BASES, RULE_SOCKETED_BASES))


def save_dir(cfg: dict) -> Path:
    return Path(os.path.expandvars(cfg["paths"]["save_dir"]))


def repo_filter(cfg: dict) -> Path:
    return ROOT / "filters" / f"{cfg['loot']['filter_name']}.fltr"


def live_filter(cfg: dict) -> Path:
    return save_dir(cfg) / f"{cfg['loot']['filter_name']}.fltr"


def read_filter(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def report(cfg: dict, stash: Path | None = None, tables: Path | None = None) -> dict:
    """What the Chronicle has and still needs, and whether the installed filter matches."""
    chron = parse_chronicle((stash or save_dir(cfg) / STASH_FILE).read_bytes())
    uniques, sets = load_tables(tables or Path(cfg["loot"]["chronicle_tables"]))
    miss_u, miss_s = missing(uniques, sets, chron)
    unique_codes, set_codes = {r["code"] for r in miss_u}, {r["item"] for r in miss_s}
    live = live_filter(cfg)
    return {
        "uniques": {"found": len(chron.uniques), "total": len(eligible(uniques)), "codes": len(unique_codes)},
        "sets": {"found": len(chron.sets), "total": len(eligible(sets)), "codes": len(set_codes)},
        "runewords": len(chron.runewords),
        "missing_uniques": [{"name": r["index"], "code": r["code"]} for r in miss_u],
        "missing_sets": [{"name": r["index"], "code": r["item"]} for r in miss_s],
        "unique_codes": sorted(unique_codes), "set_codes": sorted(set_codes),
        "up_to_date": live.exists() and up_to_date(read_filter(live), unique_codes, set_codes),
    }
