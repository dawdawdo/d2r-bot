"""New armor and weapon bases, read from the save backups (exact, unlike the screen).

On screen a white label that isn't a key or rejuv is logged as a "gem": gems, skulls and bases all have white names.
To know what really came in, each session start compares the new backup with the previous one and lists every white
or superior armor / weapon (no runeword) that wasn't there before: in Blizzaga's stash, inventory or cube, or in the
shared stash. Each one is logged ("new base: ...") and appended to logs/bases.csv.
Anything Stephen found while playing between the two backups shows up too.
"""
from __future__ import annotations

import csv
import logging
import re
import time
from pathlib import Path

from . import d2save
from .config import ROOT

log = logging.getLogger(__name__)
STASH = "ModernSharedStashSoftCoreV2.d2i"
CSV = ROOT / "logs" / "bases.csv"
BASE_QUALITIES = {"Normal", "Superior"}
_names: dict[str, str] | None = None


def base_name(code: str) -> str:
    global _names
    if _names is None:
        _names = {}
        d2save.tables()  # makes sure txt105/ is extracted
        for fn in ("armor.txt", "weapons.txt"):
            lines = (ROOT / "armory" / "work" / "txt105" / fn).read_text(encoding="utf-8", errors="replace").splitlines()
            head = lines[0].split("\t")
            ic, iname = head.index("code"), head.index("name")
            for ln in lines[1:]:
                f = ln.split("\t")
                if len(f) > max(ic, iname) and f[ic]:
                    _names.setdefault(f[ic], f[iname])
    return _names.get(code, code)


def bases_in(items: list[dict], where: str) -> list[dict]:
    t = d2save.tables()
    out = []
    for it in items:
        info = t.items.get(it["code"]) or {}
        if not (info.get("armor") or info.get("weapon")) or it["quality"] not in BASE_QUALITIES or it["runeword_id"]:
            continue
        if (it.get("position") or {}).get("mode") not in ("Stored",):  # worn gear isn't a find
            continue
        code = d2save.code_str(it["code"])
        out.append({"key": (it["code"], it["seed"]), "code": code, "name": base_name(code),
                    "kind": "armor" if info.get("armor") else "weapon", "quality": it["quality"],
                    "eth": "ETHEREAL" in it["flags"], "sockets": len(it["sockets"]), "ilvl": it["level"],
                    "defense": it.get("defense"), "where": where})
    return out


def backup_bases(backup: Path, char: str) -> list[dict]:
    out = []
    if (backup / f"{char}.d2s").exists():
        out += bases_in(d2save.read_d2s(backup / f"{char}.d2s")["items"], char)
    if (backup / STASH).exists():
        for i, tab in enumerate(d2save.read_d2i(backup / STASH)):
            out += bases_in(tab["items"], f"shared tab {i + 1}")
    return out


def previous_backup(backup: Path, char: str) -> Path | None:
    dirs = [p for p in backup.parent.glob("*") if p.is_dir() and re.fullmatch(r"\d{8}-\d{6}(_\d+)?", p.name)
            and p.name < backup.name and (p / f"{char}.d2s").exists() and (p / STASH).exists()]
    return max(dirs, key=lambda p: p.name) if dirs else None


def describe(b: dict) -> str:
    bits = [b["quality"].lower() if b["quality"] != "Normal" else "", "ethereal" if b["eth"] else "",
            f"{b['sockets']} os" if b["sockets"] else "", f"ilvl {b['ilvl']}",
            f"def {b['defense']}" if b["defense"] is not None else ""]
    return f"{b['name']} ({', '.join(x for x in bits if x)}) in {b['where']}"


def new_bases(backup: Path, char: str) -> list[dict]:
    prev = previous_backup(backup, char)
    if prev is None:
        return []
    before = {b["key"] for b in backup_bases(prev, char)}
    return [b for b in backup_bases(backup, char) if b["key"] not in before]


def report(cfg: dict, backup: Path | None = None) -> list[dict]:
    """Session start: log and record the bases that came in since the previous backup. Never raises."""
    try:
        from .armory import latest_backup

        backup = backup or latest_backup(cfg)
        char = cfg["game"].get("character")
        if backup is None or not char:
            return []
        found = new_bases(backup, char)
        for b in found:
            log.info("new base: %s", describe(b))
        if found:
            new_file = not CSV.exists()
            CSV.parent.mkdir(parents=True, exist_ok=True)
            with open(CSV, "a", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                if new_file:
                    w.writerow(["logged", "backup", "name", "code", "kind", "quality", "eth", "sockets", "ilvl",
                                "defense", "where"])
                for b in found:
                    w.writerow([time.strftime("%Y-%m-%d %H:%M"), backup.name, b["name"], b["code"], b["kind"],
                                b["quality"], int(b["eth"]), b["sockets"], b["ilvl"], b["defense"] or "", b["where"]])
        return found
    except Exception as e:  # noqa: BLE001  a bookkeeping failure must never stop a session
        log.warning("new bases unknown: %s", e)
        return []


if __name__ == "__main__":  # python -m bot.bases [--all]: bases that came in, backup by backup (no csv writes)
    import sys

    from .config import load_config

    cfg = load_config()
    char = cfg["game"]["character"]
    root = ROOT / cfg["paths"]["backups"]
    dirs = sorted(p for p in root.glob("*") if re.fullmatch(r"\d{8}-\d{6}(_\d+)?", p.name) and (p / STASH).exists())
    if "--all" not in sys.argv:
        dirs = dirs[-20:]
    for d in dirs:
        for b in new_bases(d, char):
            print(d.name, describe(b))
