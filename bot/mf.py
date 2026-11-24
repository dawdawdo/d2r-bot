"""Magic find awareness: what MF the character is wearing, read from the session-start save backup.

Stephen keeps two setups on Blizzaga: about 0 % MF (cows, for bases) and about 280 % (Mephisto, for uniques).
Meph ran for days in the 0 % setup (2026-11-11), so a boss task below its `mf.min` is swapped for LK and the
Bot page says why. Reads only backups/<ts>/<character>.d2s (bot/session.py copies the saves at every session
start) through bot/d2save.py (pure Python, both machines); never the live save folder, never the game.

Counted: stat 80 ("% better chance of getting magic items") on equipped items (not the weapon-swap slots, where
Call to Arms sits), their runeword stats and socketed jewels, and charms in the inventory. Not counted: set bonuses
(none of Stephen's MF pieces is a set item) and gems in sockets (their stats come from game tables, not the save).
"""
from __future__ import annotations

import logging
import struct
from pathlib import Path

from . import d2save
from .config import ROOT

log = logging.getLogger(__name__)
MF_STAT = 80
CHARMS = {"cm1", "cm2", "cm3"}
SWAP_SLOTS = {"RightHand", "LeftHand"}  # d2dump's names for the weapon-swap pair (d2s slots 11-12); RightArm/LeftArm = main
WORK = ROOT / "armory" / "work"


def _code(item: dict) -> str:
    c = item.get("code")
    return struct.pack("<I", c).decode("latin1").strip() if isinstance(c, int) else str(c or "").strip()


def _stat_mf(stats) -> int:
    return sum(int(s.get("value") or 0) for s in stats or [] if s.get("id") == MF_STAT)


def item_mf(item: dict) -> int:
    mf = _stat_mf(item.get("stats")) + _stat_mf(item.get("runeword_stats"))
    for s in filter(None, item.get("sockets") or []):  # jewels carry their own stats; runes and gems don't (game tables)
        mf += _stat_mf(s.get("stats"))
    return mf


def magic_find(d2s: dict) -> tuple[int, list[tuple[str, int]]]:
    """Total MF and the items it comes from, from a d2dump character JSON."""
    parts = []
    for it in d2s.get("items") or []:
        pos = it.get("position") or {}
        equipped = pos.get("mode") == "Equipped" and pos.get("body_location") not in SWAP_SLOTS
        charm = pos.get("mode") == "Stored" and pos.get("store_page") == "Inventory" and _code(it) in CHARMS
        if equipped or charm:
            mf = item_mf(it)
            if mf:
                parts.append((_code(it), mf))
    return sum(m for _, m in parts), parts


# Stephen's own inventory items, by size [w, h]: charms, tomes, cube. Wherever they sit in the save, the stowaway
# must leave them alone (2026-11-15 and 11-19: he rearranged, the config box went stale, charms/skull got stashed).
OWN_SIZES = {"cm1": (1, 1), "cm2": (1, 2), "cm3": (1, 3), "tbk": (1, 2), "ibk": (1, 2), "box": (2, 2)}


def inventory_items(d2s: dict) -> list[tuple[str, int, int]]:
    """(code, col, row) of every item in the inventory grid."""
    out = []
    for it in d2s.get("items") or []:
        p = it.get("position") or {}
        if p.get("mode") == "Stored" and p.get("store_page") == "Inventory":
            out.append((struct.pack("<I", it["code"]).decode("latin-1").strip(), p["inv_x"], p["inv_y"]))
    return out


def own_rects(items: list[tuple[str, int, int]]) -> list[list[int]]:
    """[c, r, w, h] of Stephen's charms, tomes and cube."""
    return [[c, r, *OWN_SIZES[code]] for code, c, r in items if code in OWN_SIZES]


def item_size(code: str) -> tuple[int, int]:
    """(w, h) in inventory cells, from the game tables (txt105 in the armory bundle). Unknown codes, or no tables:
    1x1, so at least the item's top-left cell is protected."""
    if code in OWN_SIZES:
        return OWN_SIZES[code]
    try:
        info = d2save.tables().items.get(d2save.code_int(code))
    except Exception:  # noqa: BLE001
        info = None
    return (info["w"] or 1, info["h"] or 1) if info else (1, 1)


def session_rects(items: list[tuple[str, int, int]], key_cell=None) -> list[list[int]]:
    """[c, r, w, h] of everything in the inventory at session start except her one working key stack (the one at
    `key_cell`, else the first): whatever is there then is Stephen's (Stephen 2026-11-21: he rearranges when he plays
    and forgets to tell; the stowaway drops spare key stacks and full-stack items, and stashes the rest)."""
    keys = sorted((c, r) for code, c, r in items if code == "key")
    work = tuple(key_cell) if key_cell and tuple(key_cell) in keys else (keys[0] if keys else None)
    return [[c, r, *item_size(code)] for code, c, r in items if not (code == "key" and (c, r) == work)]


def with_corpse(d2s: dict) -> dict:
    """The save with a corpse's gear back among the items: the session after a death reads the save before the corpse
    is picked up (2026-11-24 10:03: 31 % -> a session of LK in place of Andariel, her gear back on 30 s later)."""
    corpse = [it for c in d2s.get("corpses") or [] if isinstance(c, dict) for it in c.get("items") or []]
    return {**d2s, "items": list(d2s.get("items") or []) + corpse, "corpses": []} if corpse else d2s


def read(cfg: dict, backup: Path | None = None) -> dict | None:
    """{"mf": total, "parts": [[code, mf], ...], "backup": name} from the newest backup, or None if it can't be read
    (no backup, or the save doesn't parse)."""
    from .armory import latest_backup

    backup = backup or latest_backup(cfg)
    char = cfg["game"].get("character")
    if backup is None or not char or not (backup / f"{char}.d2s").exists():
        return None
    try:
        d2s = d2save.read_d2s(backup / f"{char}.d2s")
        worn = with_corpse(d2s)
        total, parts = magic_find(worn)
        try:  # socketed runes and gems (Ist in the Shako and Oculus: +55) live in the game tables, not the save
            from .gear import Tables, totals

            total = round(totals(worn, Tables(WORK)).get("mf", total))
        except Exception as e:  # noqa: BLE001
            log.warning("socket MF not counted: %s", e)
    except Exception as e:  # noqa: BLE001  an unreadable save must never stop a session
        log.warning("magic find unknown: %s", e)
        return None
    return {"mf": total, "parts": [list(p) for p in parts], "backup": backup.name, "inv": inventory_items(d2s)}


def gate(tasks: list, info: dict | None, cfg: dict) -> tuple[list, list[str]]:
    """Drop tasks whose `mf.min` the character doesn't meet. Returns (tasks to run, names dropped).
    Unknown MF (None) drops nothing."""
    mins = (cfg.get("mf") or {}).get("min") or {}
    if info is None:
        return tasks, []
    low = [t.name for t in tasks if info["mf"] < mins.get(t.name, 0)]
    return [t for t in tasks if t.name not in low], low
