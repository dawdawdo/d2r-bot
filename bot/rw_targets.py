"""Chronicle runewords, a few bases at a time (Stephen 2026-11-25: "slowly introduce runewords from the chronicle
without completely overwhelming the bot with bases ... maybe just target one or a few at a time").

Two parts:
- Bases already on the filter (Archon Plate, Monarch, Flail, the polearms, Diadem) fit most missing runewords. The
  cube's socket recipe rolls a random count, so a base that misses the count wanted for Spirit / CTA / CoH can carry
  a Chronicle runeword instead: `stash_bases` lists what each socketed base in the stash can still become.
- The rest need other bases. QUEUE is one base code per step, each chosen to fit several missing runewords; the
  filter shows the first `active` steps that still have a missing runeword, and only while the stash holds fewer than
  `cap` unused copies. When the Chronicle records them, the next step takes over at the next filter regeneration.

Runewords that need Jah, Cham or Zod don't keep a step open (the stash can't pay for them yet). Read-only.
"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT

WORK = ROOT / "armory" / "work"
# (base code, base name, the missing runewords it was picked for on 2026-11-25). Greedy: each step covers the most
# runewords the earlier steps and the filter's own bases don't. Reorder or trim freely.
QUEUE = [
    ("hbw", "Hunter's Bow", "Edge, Harmony, Melody, Wrath, Zephyr"),
    ("cst", "Gnarled Staff", "Leaf, Memory"),
    ("clw", "Claws", "Chaos, Pattern"),
    ("wsp", "War Scepter", "Beast, Holy Thunder"),
    ("pa1", "Targe", "Exile"),
    ("bwn", "Bone Wand", "White"),
    ("kri", "Kriss", "Ritual"),
    # 2026-11-27 Stephen: swords done but Grief, and he has a 5-socket Phase Blade for it; only Kingslayer (4 os) is left
    # for this base, so it went last and the bows (missile runewords) took the active slot.
    ("7cr", "Phase Blade", "Death, Grief, King's Grace, Kingslayer, Lawbringer, Unbending Will"),
]
ACTIVE = 1   # queue steps shown at once
CAP = 2      # stop showing a step's base once the stash holds this many unused copies
BIG = {"r31", "r32", "r33"}  # Jah, Cham, Zod


def _tsv(path: Path) -> list[dict]:
    with open(path, encoding="latin-1") as f:
        return list(csv.DictReader(f, delimiter="\t"))


@dataclass
class Tables:
    runewords: list[dict]                      # complete runewords: name, Name (RunewordN), runes, types, n
    bases: dict[str, dict]                      # base code -> row (weapons + armor with sockets)
    parents: dict[str, set[str]] = field(default_factory=dict)  # item type -> itself and every type it counts as

    def kinds(self, code: str) -> set[str]:
        b = self.bases.get(code) or {}
        return self.parents.get(b.get("type", ""), set()) | self.parents.get(b.get("type2", ""), set())

    def fits(self, code: str, rw: dict, sockets: int | None = None) -> bool:
        """Can this base carry the runeword? With `sockets`, it must have exactly that many (a socketed base)."""
        b = self.bases.get(code)
        if not b or not set(rw["types"]) & self.kinds(code):
            return False
        return rw["n"] == sockets if sockets is not None else rw["n"] <= int(b.get("gemsockets") or 0)


def load(work: Path = WORK) -> Tables:
    from . import d2save

    d2save.tables()  # extracts txt105/ and xl/ from the tracked bundle if needed
    types = {r["Code"]: r for r in _tsv(work / "txt105" / "itemtypes.txt") if r.get("Code")}

    def up(t: str, seen: set[str]) -> set[str]:
        if t and t not in seen and t in types:
            seen.add(t)
            for k in ("Equiv1", "Equiv2"):
                up(types[t].get(k, ""), seen)
        return seen

    parents = {t: up(t, set()) for t in types}
    bases = {}
    for fn in ("weapons.txt", "armor.txt"):
        for r in _tsv(work / "txt105" / fn):
            if r.get("code") and (r.get("gemsockets") or "").isdigit() and int(r["gemsockets"]) > 0:
                bases[r["code"]] = r
    rws = []
    for r in _tsv(work / "xl" / "runes.txt"):
        if r.get("complete") == "1":
            runes = [r[f"Rune{i}"] for i in range(1, 7) if r.get(f"Rune{i}")]
            rws.append(dict(name=r["*Rune Name"], key=r["Name"], runes=runes, n=len(runes),
                            types=[r[f"itype{i}"] for i in range(1, 7) if r.get(f"itype{i}")]))
    return Tables(rws, bases, parents)


def chronicle_name(item_id: int, t: Tables) -> str | None:
    """Runeword name for a Chronicle runeword id (offsets from armory/chron.py, checked there against made items:
    Call to Arms 20519, Spirit 20635; the Reign of the Warlock ones sit above 27000)."""
    n = item_id - 27189 if item_id > 27000 else (item_id - 20506 if item_id - 20506 < 80 else item_id - 20505)
    return next((r["name"] for r in t.runewords if r["key"] == f"Runeword{n}"), None)


def missing(chron_ids: set[int], t: Tables) -> list[dict]:
    have = {chronicle_name(i, t) for i in chron_ids}
    return [r for r in t.runewords if r["name"] not in have]


def targets(chron_ids: set[int], t: Tables, stash: Counter, active: int = ACTIVE, cap: int = CAP,
            queue=QUEUE, filter_codes=()) -> list[dict]:
    """Queue steps still open, in order: {code, name, runewords, stash, shown}. Each missing, affordable runeword
    belongs to the first base that fits it: the filter's own runeword bases (`filter_codes`) first, then the queue,
    so a step stays open only for runewords nothing before it can carry. The first `active` open steps are shown
    unless the stash already holds `cap` copies."""
    want = [r for r in missing(chron_ids, t) if not set(r["runes"]) & BIG]
    want = [r for r in want if not any(t.fits(c, r) for c in filter_codes)]
    out = []
    for code, name, _ in queue:
        rws = [r["name"] for r in want if t.fits(code, r)]
        want = [r for r in want if r["name"] not in rws]
        if rws:
            out.append(dict(code=code, name=name, runewords=rws, stash=stash.get(code, 0), shown=False))
    for step in out[:active]:
        step["shown"] = step["stash"] < cap
    return out


def stash_items(cfg: dict) -> list[tuple[dict, str]]:
    """(item, where) for the shared stash tabs and the bot character's own save (stash, inventory, cube)."""
    from . import d2save

    sd = Path(__import__("os").path.expandvars(cfg["paths"]["save_dir"]))
    tabs = d2save.read_d2i(sd / "ModernSharedStashSoftCoreV2.d2i")
    out = [(it, f"shared tab {i + 1}") for i, tab in enumerate(tabs) for it in tab.get("items") or []]
    d2s = d2save.read_d2s(sd / f"{cfg['game']['character']}.d2s")
    out += [(it, cfg["game"]["character"]) for it in d2s.get("items") or []
            if (it.get("position") or {}).get("mode") == "Stored"]
    return out


def stash_bases(items: list[tuple[dict, str]], t: Tables, chron_ids: set[int]) -> tuple[Counter, list[dict]]:
    """(unused base copies by code, socketed bases with the missing runewords their exact socket count fits)."""
    from . import d2save

    want = missing(chron_ids, t)
    counts, socketed = Counter(), []
    for it, where in items:
        code = d2save.code_str(it["code"]).strip()
        if code not in t.bases or it.get("quality") not in ("Normal", "Superior") or it.get("runeword_id") is not None \
                or "RUNEWORD" in str(it.get("flags")) or any(it.get("sockets") or []):
            continue
        counts[code] += 1
        n = len(it.get("sockets") or [])  # one entry per socket, None while empty (as bot/bases.py counts them)
        if n:
            socketed.append(dict(code=code, name=t.bases[code].get("name", code), sockets=n, where=where,
                                 eth="ETHEREAL" in str(it.get("flags")),
                                 runewords=[r["name"] for r in want if t.fits(code, r, n)]))
    return counts, socketed
