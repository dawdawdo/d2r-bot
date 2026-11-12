"""Magic find awareness: what MF the character is wearing, read from the session-start save backup.

Stephen keeps two setups on Blizzaga: about 0 % MF (cows, for bases) and about 280 % (Mephisto, for uniques).
Meph ran for days in the 0 % setup (2026-11-11), so a boss task below its `mf.min` is swapped for LK and the
Bot page says why. Reads only backups/<ts>/<character>.d2s (bot/session.py copies the saves at every session
start) through the armory's d2dump; never the live save folder, never the game.

Counted: stat 80 ("% better chance of getting magic items") on equipped items (not the weapon-swap slots, where
Call to Arms sits), their runeword stats and socketed jewels, and charms in the inventory. Not counted: set bonuses
(none of Stephen's MF pieces is a set item) and gems in sockets (their stats come from game tables, not the save).
"""
from __future__ import annotations

import json
import logging
import struct
import subprocess
import tarfile
from pathlib import Path

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


def _d2dump() -> Path | None:
    exe = WORK / "d2dump"
    if not exe.exists():
        bundle = ROOT / "armory" / "scanbundle.tgz"
        if not bundle.exists():
            return None
        WORK.mkdir(parents=True, exist_ok=True)
        with tarfile.open(bundle) as t:
            t.extractall(WORK, filter="data")
        exe.chmod(0o755)
    return exe


def read(cfg: dict, backup: Path | None = None) -> dict | None:
    """{"mf": total, "parts": [[code, mf], ...], "backup": name} from the newest backup, or None if it can't be read
    (no backup, or d2dump doesn't run here: it's a Linux build, so Singularity gets None and no MF gate)."""
    from .armory import latest_backup

    backup = backup or latest_backup(cfg)
    char = cfg["game"].get("character")
    if backup is None or not char or not (backup / f"{char}.d2s").exists():
        return None
    try:
        exe = _d2dump()
        if exe is None:
            return None
        out = subprocess.run([str(exe), "c", str(backup / f"{char}.d2s")], capture_output=True, check=True,
                             timeout=60).stdout
        d2s = json.loads(out)
        total, parts = magic_find(d2s)
        try:  # socketed runes and gems (Ist in the Shako and Oculus: +55) live in the game tables, not the save
            from .gear import Tables, totals

            total = round(totals(d2s, Tables(WORK)).get("mf", total))
        except Exception as e:  # noqa: BLE001
            log.warning("socket MF not counted: %s", e)
    except Exception as e:  # noqa: BLE001  an unreadable save must never stop a session
        log.warning("magic find unknown: %s", e)
        return None
    return {"mf": total, "parts": [list(p) for p in parts], "backup": backup.name}


def gate(tasks: list, info: dict | None, cfg: dict) -> tuple[list, list[str]]:
    """Drop tasks whose `mf.min` the character doesn't meet. Returns (tasks to run, names dropped).
    Unknown MF (None) drops nothing."""
    mins = (cfg.get("mf") or {}).get("min") or {}
    if info is None:
        return tasks, []
    low = [t.name for t in tasks if info["mf"] < mins.get(t.name, 0)]
    return [t for t in tasks if t.name not in low], low
