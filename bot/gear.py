"""Current gear stat summary for the Bot page ("Current gear"), from the armory's d2dump character JSON.

Totals what the character sheet would show for the stats that matter to the bot: resistances in Hell, absorbs,
MF / GF, FCR / FHR / FRW / FBR with Sorceress breakpoints, damage reduction, skills, attributes, life and mana.
Counted: equipped items except the weapon-swap pair (d2dump RightHand / LeftHand; Call to Arms sits there), their
runeword stats, socketed jewels, socketed runes and gems (bonuses from gems.txt by slot), and charms in the
inventory. Not counted: set bonuses, skills and auras (Energy Shield, merc auras), shrines. Life and mana are
approximate (per-vitality / per-energy gains by class). Reads only what the armory build already dumped.
"""
from __future__ import annotations

import csv
import struct
from pathlib import Path

SWAP = {"RightHand", "LeftHand"}
CHARMS = {"cm1", "cm2", "cm3"}
SHIELD_TYPES = {"shie", "ashd", "head"}  # shields, paladin shields, necro heads (sorc orbs are weapons)
HELL_PENALTY = -100
LIFE_PER_VIT = {"Amazon": 3, "Sorceress": 2, "Necromancer": 2, "Paladin": 3, "Barbarian": 4, "Druid": 2,
                "Assassin": 3}
MANA_PER_ENE = {"Amazon": 1.5, "Sorceress": 2, "Necromancer": 2, "Paladin": 1.5, "Barbarian": 1, "Druid": 2,
                "Assassin": 1.75}
BREAKPOINTS = {"Sorceress": {"fcr": [0, 9, 20, 37, 63, 105, 200], "fhr": [0, 5, 9, 14, 20, 30, 42, 60, 86, 142, 280]}}
CLASS_ID = {"Amazon": 0, "Sorceress": 1, "Necromancer": 2, "Paladin": 3, "Barbarian": 4, "Druid": 5, "Assassin": 6}

# item stat name -> summary key (scaled where the save stores fractions)
STAT = {
    "strength": "str", "energy": "ene", "dexterity": "dex", "vitality": "vit",
    "maxhp": "life", "maxmana": "mana", "item_maxhp_percent": "life%", "item_maxmana_percent": "mana%",
    "fireresist": "fire", "lightresist": "light", "coldresist": "cold", "poisonresist": "poison",
    "maxfireresist": "fire_max", "maxlightresist": "light_max", "maxcoldresist": "cold_max",
    "maxpoisonresist": "poison_max",
    "damageresist": "dr%", "normal_damage_reduction": "dr", "magic_damage_reduction": "mdr",
    "item_magicbonus": "mf", "item_goldbonus": "gf",
    "item_fastercastrate": "fcr", "item_fastergethitrate": "fhr", "item_fastermovevelocity": "frw",
    "item_fasterblockrate": "fbr", "item_fasterattackrate": "ias",
    "item_allskills": "skills",
    "item_absorbfire_percent": "abs_fire%", "item_absorbfire": "abs_fire", "item_absorblight_percent": "abs_light%",
    "item_absorblight": "abs_light", "item_absorbcold_percent": "abs_cold%", "item_absorbcold": "abs_cold",
    "item_absorbmagic_percent": "abs_magic%", "item_absorbmagic": "abs_magic",
    "item_cannotbefrozen": "cbf",
    "passive_fire_mastery": "mastery_fire", "passive_ltng_mastery": "mastery_light",
    "passive_cold_mastery": "mastery_cold", "passive_pois_mastery": "mastery_poison",
    "passive_fire_pierce": "pierce_fire", "passive_ltng_pierce": "pierce_light",
    "passive_cold_pierce": "pierce_cold", "passive_pois_pierce": "pierce_poison",
    "lifedrainmindam": "leech_life", "manadrainmindam": "leech_mana", "item_manaafterkill": "mana_kill",
    "hpregen": "regen", "manarecoverybonus": "mana_regen%",
}
PER_LEVEL = {"item_hp_perlevel": ("life", 2048), "item_mana_perlevel": ("mana", 2048),
             "item_find_magic_perlevel": ("mf", 8), "item_find_gold_perlevel": ("gf", 8)}
# gems.txt property code -> summary keys (socketed runes and gems store no stats in the save)
GEM_PROP = {"res-fire": ["fire"], "res-ltng": ["light"], "res-cold": ["cold"], "res-pois": ["poison"],
            "res-all": ["fire", "light", "cold", "poison"], "res-fire-max": ["fire_max"],
            "res-ltng-max": ["light_max"], "res-cold-max": ["cold_max"], "res-pois-max": ["poison_max"],
            "mag%": ["mf"], "gold%": ["gf"], "str": ["str"], "dex": ["dex"], "vit": ["vit"], "enr": ["ene"],
            "hp": ["life"], "mana": ["mana"], "red-dmg": ["dr"], "red-dmg%": ["dr%"], "red-mag": ["mdr"],
            "nofreeze": ["cbf"], "regen": ["regen"], "manasteal": ["leech_mana"], "lifesteal": ["leech_life"],
            "mana-kill": ["mana_kill"]}


def _code(c) -> str:
    return struct.pack("<I", c).decode("latin1").strip() if isinstance(c, int) else str(c or "").strip()


def _tsv(path: Path) -> list[dict]:
    with open(path, encoding="latin-1") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class Tables:
    """The bits of the game tables the summary needs, from the armory bundle (armory/work after a build)."""

    def __init__(self, work: Path) -> None:
        self.stat = {int(r["*ID"]): r["Stat"] for r in _tsv(work / "xl" / "itemstatcost.txt") if r.get("*ID", "").isdigit()}
        self.weapons = {r["code"] for r in _tsv(work / "txt105" / "weapons.txt") if r.get("code")}
        self.armor_type = {r["code"]: r.get("type", "") for r in _tsv(work / "txt105" / "armor.txt") if r.get("code")}
        self.gems = {}
        for r in _tsv(work / "xl" / "gems.txt"):
            if not r.get("code"):
                continue
            mods = {}
            for slot in ("weapon", "helm", "shield"):
                mods[slot] = [(r[f"{slot}Mod{i}Code"], int(r.get(f"{slot}Mod{i}Max") or r.get(f"{slot}Mod{i}Min") or 0))
                              for i in (1, 2, 3) if r.get(f"{slot}Mod{i}Code")]
            self.gems[r["code"]] = mods

    def slot_kind(self, code: str) -> str:
        if code in self.weapons:
            return "weapon"
        return "shield" if self.armor_type.get(code) in SHIELD_TYPES else "helm"


def _worn(d2s: dict) -> list[dict]:
    out = []
    for it in d2s.get("items") or []:
        pos = it.get("position") or {}
        if pos.get("mode") == "Equipped" and pos.get("body_location") not in SWAP:
            out.append(it)
        elif pos.get("mode") == "Stored" and pos.get("store_page") == "Inventory" and _code(it.get("code")) in CHARMS:
            out.append(it)
    return out


def totals(d2s: dict, tables: Tables) -> dict[str, float]:
    level = int((d2s.get("character") or {}).get("level") or 1)
    cls = CLASS_ID.get((d2s.get("character") or {}).get("class"), -1)
    t: dict[str, float] = {}

    def add(key: str, v: float) -> None:
        t[key] = t.get(key, 0) + v

    for it in _worn(d2s):
        stats = list(it.get("stats") or []) + list(it.get("runeword_stats") or [])
        kind = tables.slot_kind(_code(it.get("code")))
        for s in filter(None, it.get("sockets") or []):
            stats += list(s.get("stats") or [])  # jewels
            for prop, v in tables.gems.get(_code(s.get("code")), {}).get(kind, []):
                for key in GEM_PROP.get(prop, []):
                    add(key, v)
        for s in stats:
            name, v, layer = tables.stat.get(s.get("id"), ""), int(s.get("value") or 0), int(s.get("layer") or 0)
            if name in ("maxhp", "maxmana"):
                v = v / 256
            if name in PER_LEVEL:
                key, div = PER_LEVEL[name]
                add(key, v / div * level)
            elif name == "item_addclassskills":
                if layer == cls:
                    add("skills", v)
            elif name in STAT:
                add(STAT[name], v)
    return t


def _next_bp(value: float, bps: list[int]) -> str:
    nxt = next((b for b in bps if b > value), None)
    return f"next breakpoint {nxt}" if nxt is not None else "max breakpoint"


def summary(d2s: dict, tables: Tables) -> dict:
    ch = d2s.get("character") or {}
    cls, level = ch.get("class", ""), int(ch.get("level") or 1)
    t = totals(d2s, tables)
    g = lambda k: t.get(k, 0)  # noqa: E731
    base = {int(s["id"]): int(s.get("value") or 0) for s in d2s.get("stats") or []}
    quests = d2s.get("quests") or {}
    anya = sum(1 for diff in ("normal", "nightmare", "hell")
               if "REWARD_GRANTED" in str(((quests.get(diff) or {}).get("act5") or {}).get("prison_of_ice", "")))
    groups = []

    rows = []
    for el, nm in (("fire", "Fire"), ("cold", "Cold"), ("light", "Lightning"), ("poison", "Poison")):
        cap = 75 + g(f"{el}_max")
        raw = g(el) + 10 * anya + HELL_PENALTY
        note = f"over the {cap:g} cap by {raw - cap:g}" if raw > cap else f"{cap - raw:g} below the {cap:g} cap"
        rows.append([nm, f"{min(raw, cap):g}%", note])
    groups.append({"name": "Resistances (Hell)", "rows": rows,
                   "note": f"Items {HELL_PENALTY:+d} for Hell +{10 * anya} from Anya's scrolls ({anya} of 3)."})

    rows = []
    for el, nm in (("fire", "Fire"), ("cold", "Cold"), ("light", "Lightning"), ("magic", "Magic")):
        pct, flat = g(f"abs_{el}%"), g(f"abs_{el}")
        if pct or flat:
            rows.append([f"{nm} absorb", " · ".join(x for x in (f"{pct:g}%" if pct else "", f"+{flat:g}" if flat else "") if x), ""])
    if g("dr%") or g("dr"):
        rows.append(["Damage reduced", " · ".join(x for x in (f"{g('dr%'):g}%" if g("dr%") else "", f"{g('dr'):g}" if g("dr") else "") if x), ""])
    if g("mdr"):
        rows.append(["Magic damage reduced", f"{g('mdr'):g}", ""])
    rows.append(["Cannot be frozen", "yes" if g("cbf") else "no", ""])
    groups.append({"name": "Defense", "rows": rows})

    bps = BREAKPOINTS.get(cls, {})
    rows = [["Magic find", f"{g('mf'):g}%", ""], ["Gold find", f"{g('gf'):g}%", ""]]
    groups.append({"name": "Finding", "rows": rows})
    rows = []
    for key, nm in (("fcr", "Faster cast rate"), ("fhr", "Faster hit recovery"), ("frw", "Faster run/walk"),
                    ("fbr", "Faster block rate"), ("ias", "Increased attack speed")):
        if g(key) or key in bps:
            rows.append([nm, f"{g(key):g}%", _next_bp(g(key), bps[key]) if key in bps else ""])
    groups.append({"name": "Speed", "rows": rows})

    rows = [["All skills", f"+{g('skills'):g}", f"{cls} skills included"]]
    for el, nm in (("fire", "Fire"), ("cold", "Cold"), ("light", "Lightning"), ("poison", "Poison")):
        if g(f"mastery_{el}") or g(f"pierce_{el}"):
            bits = [f"+{g(f'mastery_{el}'):g}% damage" if g(f"mastery_{el}") else "",
                    f"-{g(f'pierce_{el}'):g}% enemy res" if g(f"pierce_{el}") else ""]
            rows.append([f"{nm} skills", " · ".join(b for b in bits if b), ""])
    groups.append({"name": "Skills", "rows": rows})

    vit, ene = base.get(3, 0) + g("vit"), base.get(1, 0) + g("ene")
    life = (base.get(7, 0) / 256 + g("vit") * LIFE_PER_VIT.get(cls, 2) + g("life")) * (1 + g("life%") / 100)
    mana = (base.get(9, 0) / 256 + g("ene") * MANA_PER_ENE.get(cls, 2) + g("mana")) * (1 + g("mana%") / 100)
    rows = [["Strength", f"{base.get(0, 0) + g('str'):g}", f"{base.get(0, 0)} base"],
            ["Dexterity", f"{base.get(2, 0) + g('dex'):g}", f"{base.get(2, 0)} base"],
            ["Vitality", f"{vit:g}", f"{base.get(3, 0)} base"],
            ["Energy", f"{ene:g}", f"{base.get(1, 0)} base"],
            ["Life", f"about {life:.0f}", "before skills"], ["Mana", f"about {mana:.0f}", "before skills"]]
    if g("leech_life") or g("leech_mana") or g("mana_kill") or g("regen"):
        bits = [f"{g('leech_life'):g}% life leech" if g("leech_life") else "",
                f"{g('leech_mana'):g}% mana leech" if g("leech_mana") else "",
                f"+{g('mana_kill'):g} mana per kill" if g("mana_kill") else "",
                f"+{g('regen'):g} life regen" if g("regen") else ""]
        rows.append(["Sustain", " · ".join(b for b in bits if b), ""])
    groups.append({"name": "Attributes", "rows": rows})

    return {"char": ch.get("name") or "", "class": cls, "level": level, "groups": groups,
            "note": "Worn gear (not the weapon swap) and inventory charms, socketed runes and gems included. "
                    "Set bonuses, skills and auras are not counted."}
