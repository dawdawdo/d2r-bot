"""Loot charm stats from the save, for loot.csv names. 2026-11-27 this also chose junk charms to drop; the drop step
took the wrong items (see town._loot_charm_names) and was removed on 11-28, and charm pickups are off.

Loot charms come home unidentified: the tooltip says "Grand Charm / Unidentified" and nothing more. D2R writes every
item's stats to the save, identified or not (the armory site shows them from there), and the stash stop runs at the
start of a game, when the save on disk is the one the last game wrote on save & exit, so it holds that loot, cell for
cell. `keep`/`sort` still say which charms match rules, but nothing acts on that any more: the stowaway only uses the
names (sort with KEEP_ALL), and every charm it sees goes to the stash."""
from __future__ import annotations

import logging
import struct
from pathlib import Path

from . import d2save

log = logging.getLogger(__name__)

KEEP_ALL = {"small": {"all_res": 0}, "large": {"all_res": 0}, "grand": {"all_res": 0}}  # every charm: names only
SIZES = {"cm1": ("small", (1, 1)), "cm2": ("large", (1, 2)), "cm3": ("grand", (1, 3))}
RESISTS = (39, 41, 43, 45)  # fire, lightning, cold, poison: all four equal = "All Resistances"
SKILL_TAB = 188  # +N to <class> <tab> skills; layer = class * 8 + tab
TABS = {0: "Bow", 1: "Passive", 2: "Javelin", 8: "Fire", 9: "Lightning", 10: "Cold", 16: "Curses",
        17: "Poison & Bone", 18: "Summoning", 24: "Combat (Pal)", 25: "Offensive Auras", 26: "Defensive Auras",
        32: "Combat (Barb)", 33: "Masteries", 34: "Warcries", 40: "Summoning (Dru)", 41: "Shape Shifting",
        42: "Elemental", 48: "Traps", 49: "Shadow Disciplines", 50: "Martial Arts"}  # armory/fmt.py
CLASSES = ("Amazon", "Sorceress", "Necromancer", "Paladin", "Barbarian", "Druid", "Assassin", "Warlock")
NAMES = {0: "+{} str", 1: "+{} energy", 2: "+{} dex", 3: "+{} vit", 19: "+{} AR", 21: "+{} min dmg", 22: "+{} max dmg",
         31: "+{} def", 79: "{}% gold", 80: "{}% MF", 96: "{}% FRW", 99: "{}% FHR"}


def code(it: dict) -> str:
    return struct.pack("<I", it["code"]).decode("latin-1").strip()


def traits(it: dict) -> dict[str, int]:
    """The stats keep rules ask about: all_res (the lowest of the four resists), skills (+N skill tab), mf, life."""
    st: dict[int, int] = {}
    for s in it.get("stats") or []:
        st[s["id"]] = st.get(s["id"], 0) + int(s["value"])
    return {"all_res": max(0, min(st.get(i, 0) for i in RESISTS)), "skills": st.get(SKILL_TAB, 0),
            "mf": st.get(80, 0), "life": st.get(7, 0) >> 8}


def keep(it: dict, rules: dict) -> bool:
    """Uniques always; a magic charm when any of its size's rules ({stat: at least}) holds."""
    if it.get("quality") != "Magic":
        return True
    want = rules.get(SIZES[code(it)][0]) or {}
    t = traits(it)
    return any(t.get(k, 0) >= v for k, v in want.items())


def describe(it: dict) -> str:
    """"Grand Charm: +1 Martial Arts skills; +16 life" (no commas: loot.csv is time,item)."""
    size = SIZES.get(code(it), ("?", None))[0].capitalize() + " Charm"
    if it.get("quality") != "Magic":
        return f"{str(it.get('quality')).lower()} {size}"
    t, parts, res = traits(it), [], set()
    if t["all_res"]:
        parts.append(f"{t['all_res']} all res")
        res = set(RESISTS)
    for s in it.get("stats") or []:
        i, v = s["id"], int(s["value"])
        if i in res:
            continue
        if i == SKILL_TAB:
            parts.append(f"+{v} {tab_name(s.get('layer'))} skills")
        elif i == 7:
            parts.append(f"+{v >> 8} life")
        elif i == 9:
            parts.append(f"+{v >> 8} mana")
        elif i in RESISTS:
            parts.append(f"{('fire', 'light', 'cold', 'poison')[RESISTS.index(i)]} res {v}")
        elif i in NAMES:
            parts.append(NAMES[i].format(v))
    return f"{size}: {'; '.join(parts) or 'damage only'}"


def tab_name(layer) -> str:
    """"Martial Arts"; tabs armory/fmt.py has no name for (the Warlock's): "Warlock tab 2"."""
    if layer in TABS:
        return TABS[layer]
    if isinstance(layer, int) and 0 <= layer // 8 < len(CLASSES):
        return f"{CLASSES[layer // 8]} tab {layer % 8 + 1}"
    return "class"


def read_save(cfg: dict) -> dict:
    """The character's save as D2R last wrote it (read-only)."""
    return d2save.read_d2s(Path(cfg["paths"]["save_dir"]) / f"{cfg['game']['character']}.d2s")


def footprint(c: int, r: int, size: tuple[int, int]) -> set[tuple[int, int]]:
    return {(c + dc, r + dr) for dc in range(size[0]) for dr in range(size[1])}


def sort(d2s: dict, loot_cells, rules: dict) -> tuple[list[dict], dict[tuple[int, int], dict]]:
    """Loot charms in the save's inventory: ([{cell, cells, what}] to drop, {cell: {cells, what}} to keep). Cells are
    the item's top-left inventory cell, as cell_center takes them. Nothing to drop if a loot cell on screen has no
    item in the save (the save is older than the inventory) or a charm reaches outside the loot cells."""
    from .mf import item_size

    loot = set(map(tuple, loot_cells))
    covered: set[tuple[int, int]] = set()
    junk, kept = [], {}
    for it in d2s.get("items") or []:
        p = it.get("position") or {}
        if p.get("mode") != "Stored" or p.get("store_page") != "Inventory":
            continue
        c, r, cd = p["inv_x"], p["inv_y"], code(it)
        cells = footprint(c, r, SIZES[cd][1] if cd in SIZES else item_size(cd))
        covered |= cells
        if cd not in SIZES or (c, r) not in loot:
            continue
        if not cells <= loot:
            log.warning("charms: the save's %s at (%d, %d) reaches outside the loot cells; keeping it", cd, c, r)
            kept[(c, r)] = {"cells": cells, "what": describe(it)}
        elif keep(it, rules):
            kept[(c, r)] = {"cells": cells, "what": describe(it)}
        else:
            junk.append({"cell": (c, r), "cells": cells, "what": describe(it)})
    stale = loot - covered
    if stale and junk:
        log.warning("charms: %d loot cell(s) %s aren't in the save; dropping nothing", len(stale), sorted(stale)[:4])
        kept.update({j["cell"]: {"cells": j["cells"], "what": j["what"]} for j in junk})
        junk = []
    return junk, kept
