"""Read-only D2R save parser in pure Python: .d2s character saves and the .d2i shared stash.

A line-by-line port of the read side of the Rust crate `d2s` 0.1.1 (MIT, ResurrectedTrader), which the armory's
Linux-only `d2dump` binary is built on. `read_d2s` / `read_d2i` return the same JSON-shaped dicts as `d2dump c` /
`d2dump s`, so callers can switch between the two freely; `tests/test_d2save.py` holds the comparison.

Nothing here writes: no file is opened for writing, and callers pass the session-start backup copies anyway.
Game tables (bit widths of stats, item classes) come from txt105/ in the armory bundle (version 105 only).
"""
from __future__ import annotations

import struct
from pathlib import Path

# --- bit reader -------------------------------------------------------------------------------------------------


class Reader:
    """LSB-first bit reader (the order of every bit-packed structure in D2 saves)."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0
        self.nbits = len(data) * 8

    def remaining(self) -> int:
        return max(0, self.nbits - self.pos)

    def bits(self, n: int) -> int:
        if n == 0:
            return 0
        if n > 32:
            raise ValueError("cannot read more than 32 bits at once")
        end = self.pos + n
        if end > self.nbits:
            raise EOFError(f"unexpected end of data at bit {self.pos}")
        b = self.pos >> 3
        word = int.from_bytes(self.data[b:b + 8], "little")
        v = (word >> (self.pos & 7)) & ((1 << n) - 1)
        self.pos = end
        return v

    def signed(self, n: int) -> int:
        if n == 0:
            return 0
        v = self.bits(n)
        return v - (1 << n) if n < 32 and v & (1 << (n - 1)) else _i32(v)

    def peek(self, n: int) -> int:
        p = self.pos
        try:
            return self.bits(n)
        finally:
            self.pos = p

    def u8(self) -> int:
        return self.bits(8)

    def u16(self) -> int:
        return self.bits(16)

    def u32(self) -> int:
        return self.bits(32)

    def u64(self) -> int:
        lo = self.bits(32)
        return self.bits(32) << 32 | lo

    def align(self) -> None:
        self.pos = (self.pos + 7) & ~7

    def raw(self, count: int) -> bytes:
        if self.pos & 7:
            raise ValueError("read_bytes requires byte alignment")
        s = self.pos >> 3
        if s + count > len(self.data):
            raise EOFError("unexpected end of data")
        self.pos += count * 8
        return self.data[s:s + count]

    def array(self, count: int) -> list[int]:
        return list(self.raw(count))

    def fixed_string(self, n: int) -> str:
        return self.raw(n).split(b"\0", 1)[0].decode("utf-8", "replace")

    def string8(self) -> str:
        out = bytearray()
        while len(out) < 64:
            ch = self.bits(8)
            if ch == 0:
                break
            out.append(ch)
        return out.decode("utf-8", "replace")

    def string7(self) -> str:
        out = []
        while len(out) < 32:
            ch = self.bits(7)
            if ch == 0:
                break
            out.append(chr(ch))
        return "".join(out)


def _i32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def _i64(v: int) -> int:
    v &= (1 << 64) - 1
    return v - (1 << 64) if v >> 63 else v


# --- Huffman item codes (D2R) -----------------------------------------------------------------------------------

_HUFF = [("0", 0b11111011, 8), (" ", 0b10, 2), ("1", 0b1111100, 7), ("2", 0b001100, 6), ("3", 0b1101101, 7),
         ("4", 0b11111010, 8), ("5", 0b00010110, 8), ("6", 0b1101111, 7), ("7", 0b01111, 5), ("8", 0b000100, 6),
         ("9", 0b01110, 5), ("a", 0b11110, 5), ("b", 0b0101, 4), ("c", 0b01000, 5), ("d", 0b110001, 6),
         ("e", 0b110000, 6), ("f", 0b010011, 6), ("g", 0b11010, 5), ("h", 0b00011, 5), ("i", 0b1111110, 7),
         ("j", 0b000101110, 9), ("k", 0b010010, 6), ("l", 0b11101, 5), ("m", 0b01101, 5), ("n", 0b001101, 6),
         ("o", 0b1111111, 7), ("p", 0b11001, 5), ("q", 0b11011001, 8), ("r", 0b11100, 5), ("s", 0b0010, 4),
         ("t", 0b01100, 5), ("u", 0b00001, 5), ("v", 0b1101110, 7), ("w", 0b00000, 5), ("x", 0b00111, 5),
         ("y", 0b0001010, 7), ("z", 0b11011000, 8)]


def _build_decode() -> list[tuple[int, int]]:
    table = [(0, 0)] * 512
    for sym, code, n in _HUFF:
        stream = int(format(code, f"0{n}b")[::-1], 2)  # MSB-first code -> order the bits appear in the stream
        for fill in range(1 << (9 - n)):
            table[stream | fill << n] = (ord(sym), n)
    return table


_DECODE = _build_decode()


def _huffman(r: Reader) -> int:
    out = 0
    for i in range(4):
        avail = min(r.remaining(), 9)
        sym, n = _DECODE[r.peek(avail)]
        if n == 0 or n > avail:
            raise ValueError(f"invalid Huffman item code (character {i}) at bit {r.pos}")
        r.pos += n
        out |= sym << (8 * i)
    return out


# --- enums and flags, serialized the way serde does in d2dump -----------------------------------------------------

def _enum(names: dict[int, str]):
    return lambda v: names[v] if v in names else {"Unknown": v}


BODY = _enum(dict(enumerate(["None", "Head", "Neck", "Torso", "RightArm", "LeftArm", "RightRing", "LeftRing", "Belt",
                             "Feet", "Gloves", "RightHand", "LeftHand"])))
CLASS = _enum(dict(enumerate(["Amazon", "Sorceress", "Necromancer", "Paladin", "Barbarian", "Druid", "Assassin",
                              "Warlock"])))
DIFFICULTY = _enum({0: "Normal", 1: "Nightmare", 2: "Hell"})
GAME_VERSION = _enum({0: "None", 1: "Classic", 2: "Expansion", 3: "ReignOfTheWarlock"})
MODE = _enum(dict(enumerate(["Stored", "Equipped", "InBelt", "OnGround", "OnCursor", "Dropping", "Socketed"])))
QUALITY = _enum({1: "Inferior", 2: "Normal", 3: "Superior", 4: "Magic", 5: "Set", 6: "Rare", 7: "Unique", 8: "Craft",
                 9: "Tempered"})
TAB_TYPE = _enum({0: "Normal", 1: "AdvancedStash", 2: "Chronicle"})
STORE_PAGE = _enum({0: "Inventory", 1: "Equip", 2: "Trade", 3: "Cube", 4: "Stash", 5: "Belt", 255: "Null"})
DEMON_TYPE = _enum({1: "Standard", 2: "SuperUnique"})


def _flags(names: list[tuple[str, int]]):
    """bitflags 2 serde text: names of set flags joined by ' | ', leftover bits as hex."""
    def fmt(bits: int) -> str:
        parts, rest = [], bits
        for name, f in names:
            if not rest:
                break
            if bits & f == f and rest & f:
                parts.append(name)
                rest &= ~f
        if rest:
            parts.append(f"0x{rest:x}")
        return " | ".join(parts)
    return fmt


CHAR_FLAGS = _flags([("INIT", 0x1), ("REALM_CHAR", 0x2), ("HARDCORE", 0x4), ("DEAD", 0x8), ("SAVE_PROCESS", 0x10),
                     ("EXPANSION", 0x20), ("LADDER", 0x40), ("NEEDS_RENAMING", 0x80), ("WEAPON_SWITCH", 0x2000)])
ITEM_FLAG_BITS = [("NEW_ITEM", 0x1), ("TARGET", 0x2), ("TARGETING", 0x4), ("DELETED", 0x8), ("IDENTIFIED", 0x10),
                  ("HAS_QUANTITY", 0x20), ("SWITCH_IN", 0x40), ("SWITCH_OUT", 0x80), ("BROKEN", 0x100),
                  ("REPAIRED", 0x200), ("SOCKETED", 0x800), ("NO_SELL", 0x1000), ("IN_STORE", 0x2000),
                  ("NO_EQUIP", 0x4000), ("NAMED", 0x8000), ("IS_EAR", 0x10000), ("STARTER_ITEM", 0x20000),
                  ("INIT", 0x80000), ("COMPACT_SAVE", 0x200000), ("ETHEREAL", 0x400000), ("JUST_SAVED", 0x800000),
                  ("PERSONALIZED", 0x1000000), ("LOW_QUALITY", 0x2000000), ("RUNEWORD", 0x4000000),
                  ("DUPLICATED", 0x8000000), ("CHRONICLE", 0x10000000), ("CHRONICLE_COMPACT", 0x20000000)]
ITEM_FLAGS = _flags(ITEM_FLAG_BITS)
F = {n: b for n, b in ITEM_FLAG_BITS}
QUEST_FLAGS = _flags([(n, 1 << i) for i, n in enumerate(
    ["REWARD_GRANTED", "REWARD_PENDING", "STARTED", "LEFT_TOWN", "ENTER_AREA", "CUSTOM1", "CUSTOM2", "CUSTOM3",
     "CUSTOM4", "CUSTOM5", "CUSTOM6", "CUSTOM7", "QUEST_LOG", "PRIMARY_GOAL_ACHIEVED", "COMPLETED_NOW",
     "COMPLETED_BEFORE"])])


def _wp(names: str):
    return _flags([(n, 1 << i) for i, n in enumerate(names.split())])


WP_ACTS = [
    (9, _wp("ROGUE_ENCAMPMENT COLD_PLAINS STONY_FIELD DARK_WOOD BLACK_MARSH OUTER_CLOISTER JAIL_LEVEL1 INNER_CLOISTER "
            "CATACOMBS_LEVEL2")),
    (9, _wp("LUT_GHOLEIN SEWERS_LEVEL2 DRY_HILLS HALLS_OF_THE_DEAD_LEVEL2 FAR_OASIS LOST_CITY PALACE_CELLAR_LEVEL1 "
            "ARCANE_SANCTUARY CANYON_OF_THE_MAGI")),
    (9, _wp("KURAST_DOCKS SPIDER_FOREST GREAT_MARSH FLAYER_JUNGLE LOWER_KURAST KURAST_BAZAAR UPPER_KURAST TRAVINCAL "
            "DURANCE_OF_HATE_LEVEL2")),
    (3, _wp("THE_PANDEMONIUM_FORTRESS CITY_OF_THE_DAMNED RIVER_OF_FLAME")),
    (9, _wp("HARROGATH FRIGID_HIGHLANDS ARREAT_PLATEAU CRYSTALLINE_PASSAGE HALLS_OF_PAIN GLACIAL_TRAIL FROZEN_TUNDRA "
            "THE_ANCIENTS_WAY WORLDSTONE_KEEP_LEVEL2")),
]
QUEST_ACTS = [
    "introduction den_of_evil sisters_burial_grounds tools_of_the_trade the_search_for_cain the_forgotten_tower "
    "sisters_to_the_slaughter completion",
    "introduction radaments_lair the_horadric_staff tainted_sun arcane_sanctuary the_summoner the_seven_tombs completion",
    "introduction lam_esens_tome khalims_will blade_of_the_old_religion the_golden_bird the_blackened_temple "
    "the_guardian completion",
    "introduction the_fallen_angel terrors_end hellforge completion flavie_gossip guard_gossip1 guard_gossip2",
    "dark_wanderer hadriel_gossip unused34 siege_on_harrogath rescue_on_mount_arreat prison_of_ice "
    "betrayal_of_harrogath rite_of_passage eve_of_destruction akara_respec unused42 unused43 unused44 unused45 "
    "unused46 unused47",
]

# stat ids
ARMOR_CLASS, DURABILITY, MAX_DURABILITY, NUM_SOCKETS, QUEST_ITEM_DIFFICULTY = 31, 72, 73, 194, 356
POISON_MIN_DAMAGE, POISON_COUNT, TERMINATOR = 57, 326, 511
PAIRED = {17: (18,), 48: (49,), 50: (51,), 52: (53,), 54: (55, 56), 57: (58, 59)}

V100_STACKABLE = set(
    "rvs rvl gcv gfv gsv gzv gpv gcy gfy gsy gly gpy gcb gfb gsb glb gpb gcg gfg gsg glg gpg gcr gfr gsr glr gpr gcw "
    "gfw gsw glw gpw skc skf sku skl skz r01 r02 r03 r04 r05 r06 r07 r08 r09 r10 r11 r12 r13 r14 r15 r16 r17 r18 r19 "
    "r20 r21 r22 r23 r24 r25 r26 r27 r28 r29 r30 r31 r32 r33 pk1 pk2 pk3 dhn bey mbr toa tes ceh bet fed".split())


def code_int(code: str) -> int:
    return struct.unpack("<I", code.ljust(4)[:4].encode("latin-1"))[0]


def code_str(code: int) -> str:
    return struct.pack("<I", code).decode("latin-1").rstrip(" \0")


# --- game tables -------------------------------------------------------------------------------------------------

class Tables:
    """Stat bit widths and item classes from the version-105 .txt files (d2s crate's TxtData)."""

    def __init__(self, txt_dir: Path) -> None:
        def rows(name: str):
            text = (txt_dir / name).read_bytes().decode("utf-8", "replace").lstrip("﻿")
            lines = [ln for ln in text.split("\n") if ln]
            head = [c.strip() for c in lines[0].rstrip("\r").split("\t")]
            low = {}
            for i, c in enumerate(head):
                if c:
                    low.setdefault(c.lower(), i)
            return low, [ln.rstrip("\r") for ln in lines[1:]]

        def col(cols, idx):
            return cols[idx].strip() if idx is not None and idx < len(cols) else ""

        def num(s):
            try:
                return int(s)
            except ValueError:
                return 0

        def u8(s):
            n = num(s)
            return n if 0 <= n <= 255 and s.lstrip("+").isdigit() else 0

        # itemstatcost: one entry per line, in line order (that order is the stat id)
        h, lines = rows("itemstatcost.txt")
        c = {k: h.get(k.lower()) for k in ("CSvSigned", "CSvBits", "CSvParam", "Save Bits", "Save Param Bits",
                                          "Save Add", "ValShift")}
        self.stats = []
        for ln in lines:
            if not ln.strip():
                self.stats.append((0, 0, False, 0, 0, 0, 0))
                continue
            cols = ln.split("\t")
            g = lambda k: col(cols, c[k])  # noqa: E731
            sg = g("CSvSigned")
            self.stats.append((u8(g("CSvBits")), u8(g("CSvParam")), sg == "1" or sg.lower() == "true",
                               u8(g("Save Bits")), num(g("Save Param Bits")), num(g("Save Add")), u8(g("ValShift"))))

        # itemtypes: hierarchy via Equiv1/Equiv2
        h, lines = rows("itemtypes.txt")
        ic, e1, e2, gfx = h.get("code"), h.get("equiv1"), h.get("equiv2"), h.get("varinvgfx")
        types, equivs, by_name = [], [], {}
        for ln in lines:
            if not ln.strip():
                continue
            cols = ln.split("\t")
            code = col(cols, ic)
            if not code:
                types.append((0, 0))
                equivs.append(("", ""))
                continue
            by_name.setdefault(code.lower(), len(types))
            types.append((code_int(code), u8(col(cols, gfx))))
            equivs.append((col(cols, e1), col(cols, e2)))
        children = [[] for _ in types]
        for i, (a, b) in enumerate(equivs):
            for name in (a, b):
                p = by_name.get(name.lower()) if name else None
                if p:  # index 0 is never a parent
                    children[p].append(i)
        type_index = {}
        for i, (tc, _) in enumerate(types):
            if tc:
                type_index.setdefault(code_str(tc).lower(), i)

        def below(target: str) -> set[int]:
            t = code_int(target)
            out, seen = set(), [False] * len(types)
            stack = [i for i, (tc, _) in enumerate(types) if tc == t]
            while stack:
                i = stack.pop()
                if seen[i]:
                    continue
                seen[i] = True
                if types[i][0]:
                    out.add(types[i][0])
                stack.extend(children[i])
            return out

        sets = {k: below(k) for k in ("armo", "weap", "gold", "char", "body", "play", "scro", "book")}
        self.items: dict[int, dict] = {}
        for name in ("weapons.txt", "armor.txt", "misc.txt"):
            h, lines = rows(name)
            k = {x: h.get(x) for x in ("code", "type", "compactsave", "stackable", "quest", "questdiffcheck",
                                       "invwidth", "invheight")}
            for ln in lines:
                if not ln.strip():
                    continue
                cols = ln.split("\t")
                code = col(cols, k["code"])
                if not code:
                    continue
                ci = code_int(code)
                if ci in self.items:
                    continue
                tname = col(cols, k["type"])
                ti = type_index.get(tname.lower(), 0) if tname else 0
                tcode, tgfx = types[ti] if ti < len(types) else (0, 0)
                isin = lambda s: bool(tcode) and tcode in sets[s]  # noqa: E731,B023
                self.items[ci] = {
                    "compact": u8(col(cols, k["compactsave"])) != 0, "gfx": tgfx > 0,
                    "armor": isin("armo"), "weapon": isin("weap"), "gold": isin("gold"),
                    "stackable": u8(col(cols, k["stackable"])) != 0, "charm": isin("char"),
                    "body": isin("body"), "player_body": isin("play"), "scroll_book": isin("scro") or isin("book"),
                    "quest": u8(col(cols, k["quest"])) != 0, "quest_diff": u8(col(cols, k["questdiffcheck"])) != 0,
                    "w": u8(col(cols, k["invwidth"])), "h": u8(col(cols, k["invheight"])),
                }

    def stat(self, sid: int):
        if sid >= len(self.stats):
            raise ValueError(f"unknown stat {sid}")
        return self.stats[sid]  # (csv_bits, csv_param, csv_signed, save_bits, save_param_bits, save_add, val_shift)

    def item(self, code: int) -> dict:
        info = self.items.get(code)
        if info is None:
            raise ValueError(f"unknown item code {code_str(code)!r}")
        return info


# --- items -------------------------------------------------------------------------------------------------------

def _stat_list(r: Reader, t: Tables) -> list[dict]:
    out = []
    while True:
        sid = r.bits(9)
        if sid == TERMINATOR:
            return out
        _, _, _, sb, spb, sa, vs = t.stat(sid)
        layer = r.bits(spb) if spb > 0 else 0
        raw = _i32(r.bits(sb) - sa)
        out.append({"id": sid, "layer": layer, "value": _i64(raw << vs)})
        for p in PAIRED.get(sid, ()):
            _, _, _, psb, _, psa, pvs = t.stat(p)
            out.append({"id": p, "layer": 0, "value": _i64(_i32(r.bits(psb) - psa) << pvs)})
        if sid == POISON_MIN_DAMAGE:
            out.append({"id": POISON_COUNT, "layer": 0, "value": 1})


def _prefix(r: Reader) -> int:
    return r.bits(11)  # magic prefix offset is 0 for D2R versions


def _quality_data(r: Reader, q: int, info: dict):
    if q == 1:
        return {"Inferior": {"file_index": r.bits(3)}}
    if q == 3:
        return {"Superior": {"file_index": r.bits(3)}}
    if q == 4:
        return {"Magic": {"prefix": _prefix(r), "suffix": r.bits(11)}}
    if q in (5, 7):
        return {"SetUnique": {"file_index": r.bits(12)}}
    if q in (6, 8):
        d = {"name_prefix": r.u8(), "name_suffix": r.u8(), "prefixes": [0, 0, 0], "suffixes": [0, 0, 0]}
        for i in range(3):
            if r.bits(1):
                d["prefixes"][i] = _prefix(r)
            if r.bits(1):
                d["suffixes"][i] = r.bits(11)
        return {"RareCraft": d}
    if q == 9:
        return {"Tempered": {"name_prefix": r.u8(), "name_suffix": r.u8()}}
    if q == 2:
        if info["charm"]:
            if r.bits(1):
                return {"NormalCharm": {"has_prefix": True, "prefix": _prefix(r), "suffix": 0}}
            return {"NormalCharm": {"has_prefix": False, "prefix": 0, "suffix": r.bits(11)}}
        if info["body"] and not info["player_body"]:
            return {"NormalBodyPart": {"file_index": r.bits(10)}}
        if info["scroll_book"]:
            return {"NormalScrollBook": {"spell_type": r.bits(5)}}
    return None


def _new_item() -> dict:
    return {"flags": 0, "version": 0, "position": None, "code": 0, "ear_file_index": 0, "ear_level": 0,
            "ear_name": "", "gold_amount": 0, "player_gold": False, "quest_difficulty": None, "seed": 0, "level": 0,
            "quality": 0, "variable_gfx_id": None, "auto_affix_id": None, "quality_data": None, "runeword_id": None,
            "personalized_name": "", "realm_data": None, "defense": None, "max_durability": None, "durability": None,
            "quantity": None, "set_item_mask": None, "stats": [], "set_bonus_stats": [], "runeword_stats": None,
            "sockets": [], "chronicle_id": None, "chronicle_timestamp": None, "chronicle_recipients": None,
            "advanced_stash_stack_size": None}


def _position(r: Reader, mode: int) -> dict:
    p = {"mode": MODE(mode), "ground_x": 0, "ground_y": 0, "body_location": BODY(0), "inv_x": 0, "inv_y": 0,
         "store_page": STORE_PAGE(0)}
    if mode in (3, 5):
        p["ground_x"], p["ground_y"] = r.u16(), r.u16()
    else:
        p["body_location"] = BODY(r.bits(4))
        p["inv_x"], p["inv_y"] = r.bits(4), r.bits(4)
        p["store_page"] = STORE_PAGE((r.bits(3) - 1) & 0xFF)
    return p


def _format(r: Reader, v: int) -> int:
    if v > 96:
        high = r.bits(1)
        val = r.bits(2)
        return val + 99 if high else val
    return r.bits(10)


def _code(r: Reader, v: int) -> int:
    return _huffman(r) if v > 96 else r.u32()


def _string(r: Reader, v: int) -> str:
    return r.string8() if v > 97 else r.string7()


def _gold(r: Reader, it: dict, v: int) -> None:
    it["gold_amount"] = r.u32() if r.bits(1) else r.bits(12)
    if v > 96:
        it["player_gold"] = bool(r.bits(1))


def _realm(r: Reader, it: dict, v: int) -> None:
    if v <= 86 or not r.bits(1):
        return
    it["realm_data"] = [r.u32() for _ in range(4 if v >= 97 else 3 if v >= 94 else 2)]


def _adv_stack(r: Reader, it: dict, v: int) -> None:
    if v <= 99:
        return
    present = code_str(it["code"]) in V100_STACKABLE if v <= 101 else bool(r.bits(1))
    if present:
        it["advanced_stash_stack_size"] = r.u8()


def _durability(r: Reader, it: dict, t: Tables) -> None:
    _, _, _, msb, _, msa, _ = t.stat(MAX_DURABILITY)
    _, _, _, dsb, _, dsa, _ = t.stat(DURABILITY)
    mx = _i32(r.bits(msb) - msa)
    it["max_durability"] = mx
    if mx > 0:
        it["durability"] = _i32(r.bits(dsb) - dsa)


def read_item(r: Reader, t: Tables, v: int) -> dict:
    it = _new_item()
    if v <= 96 and r.u16() != 0x4D4A:
        raise ValueError("bad item magic")
    flags = r.u32()
    gamble = bool(flags & F["LOW_QUALITY"])
    flags &= ~(F["LOW_QUALITY"] | F["INIT"])
    it["flags"] = flags
    filled = 0
    try:
        it["version"] = _format(r, v)
        mode = r.bits(3)
        it["position"] = _position(r, mode)
        if flags & F["COMPACT_SAVE"]:
            if flags & F["IS_EAR"]:
                it["code"] = code_int("ear")
                it["ear_file_index"], it["ear_level"] = r.bits(3), r.bits(7)
                it["ear_name"] = _string(r, v)
            else:
                it["code"] = _code(r, v)
                if t.item(it["code"])["gold"]:
                    _gold(r, it, v)
            info = t.item(it["code"])
            if v > 92 and info["quest"] and info["quest_diff"]:
                _, _, _, sb, _, sa, vs = t.stat(QUEST_ITEM_DIFFICULTY)
                it["quest_difficulty"] = DIFFICULTY(((_i32(r.bits(sb) - sa)) << vs) & 0xFF)
            _realm(r, it, v)
            _adv_stack(r, it, v)
            it["level"], it["quality"] = 1, 2
        else:
            it["code"] = _code(r, v)
            if gamble:
                it["level"], it["quality"] = 1, 1
            else:
                filled = r.bits(3)
                it["sockets"] = [None] * filled
                it["seed"] = r.u32()
                it["level"] = max(r.bits(7), 1)
                it["quality"] = r.bits(4)
                if r.bits(1):
                    it["variable_gfx_id"] = r.bits(3)
                if r.bits(1):
                    it["auto_affix_id"] = r.bits(11) & 0xFFFF
                info = t.item(it["code"])
                it["quality_data"] = _quality_data(r, it["quality"], info)
                if flags & F["RUNEWORD"]:
                    it["runeword_id"] = r.u16()
                if flags & F["IS_EAR"]:
                    it["ear_file_index"], it["ear_level"] = r.bits(3), r.bits(7)
                    it["ear_name"] = _string(r, v)
                elif flags & F["PERSONALIZED"]:
                    it["personalized_name"] = _string(r, v)
                _realm(r, it, v)
                if info["armor"]:
                    _, _, _, sb, _, sa, _ = t.stat(ARMOR_CLASS)
                    it["defense"] = _i32(r.bits(sb) - sa)
                    _durability(r, it, t)
                elif info["weapon"]:
                    _durability(r, it, t)
                elif info["gold"]:
                    _gold(r, it, v)
                if v > 104:
                    if r.bits(1):
                        it["quantity"] = r.bits(9)
                elif info["stackable"]:
                    it["quantity"] = r.bits(9 if v > 80 else 8)
                if flags & F["SOCKETED"]:
                    count = r.bits(t.stat(NUM_SOCKETS)[3])
                    if count < filled:
                        raise ValueError(f"socket count {count} < {filled} socketed items")
                    it["sockets"] = [None] * count
                if it["quality"] == 5:
                    it["set_item_mask"] = r.bits(5)
                it["stats"] = _stat_list(r, t)
                if it["quality"] == 5:
                    for i in range(5):
                        if it["set_item_mask"] & (1 << i):
                            it["set_bonus_stats"].append(_stat_list(r, t))
                if flags & F["RUNEWORD"]:
                    it["runeword_stats"] = _stat_list(r, t)
                if v > 99 and flags & F["CHRONICLE"]:
                    it["chronicle_id"] = r.u16()
                    compact = bool(flags & F["CHRONICLE_COMPACT"])
                    if not compact:
                        it["chronicle_timestamp"] = r.u32()
                    n = 1 if compact else min(r.bits(4), 8)
                    if n:
                        it["chronicle_recipients"] = [r.u32() | r.u32() << 32 for _ in range(n)]
                _adv_stack(r, it, v)
    except (ValueError, EOFError) as e:
        raise ValueError(f"item {code_str(it['code'])!r} flags {flags:#x} at bit {r.pos}: {e}") from e
    r.align()  # every item is serialized into its own byte buffer
    for i in range(filled):
        it["sockets"][i] = read_item(r, t, v)
    it["flags"] = ITEM_FLAGS(flags)
    it["quality"] = QUALITY(it["quality"])
    return it


def read_items(r: Reader, t: Tables, v: int, what: str = "items section") -> list[dict]:
    if r.u16() != 0x4D4A:
        raise ValueError(f"bad {what} magic")
    return [read_item(r, t, v) for _ in range(r.u16())]


# --- character save ----------------------------------------------------------------------------------------------

def _skill(r: Reader) -> dict:
    raw = r.u16()
    return {"skill_id": raw & 0x7FFF, "side": "Left" if raw >> 15 else "Right", "item_index": r.u16()}


def _preview_item(r: Reader) -> dict:
    return {"code": r.u32(), "transform": r.u8(), "quality": QUALITY(r.u8()), "file_index": r.u16(),
            "flags": ITEM_FLAGS(r.u32())}


def _character(r: Reader, v: int) -> dict:
    c = {"weapon_switch": r.u32(), "name": r.fixed_string(16) if v < 104 else ""}
    flags = r.u32()
    c["flags"] = CHAR_FLAGS(flags)
    c["class"] = CLASS(r.u8())
    c["num_stats"], c["num_skills"], c["level"] = r.u8(), r.u8(), r.u8()
    c["create_time"], c["last_save_time"], c["play_time"] = r.u32(), r.u32(), r.u32()
    c["skill_hotkeys"] = [_skill(r) for _ in range(16)]
    for k in ("left_skill", "right_skill", "switch_left_skill", "switch_right_skill"):
        c[k] = _skill(r)
    c["appearance_graphics"], c["appearance_tints"] = r.array(16), r.array(16)
    c["town_difficulty"] = r.array(3)
    c["map_seed"] = r.u32()
    c["merc"] = {"flags": r.u32(), "seed": r.u32(), "name_index": r.u16(), "hireling_id": r.u16(),
                 "experience": r.u32()}
    p = {}
    if v >= 104:
        p["save_times"] = [r.u64() for _ in range(6)]
        p["experiences"] = [r.u32() for _ in range(6)]
        p["guild_emblem_color"], gv, p["preview_padding"] = r.u8(), r.u8(), r.u16()
    else:
        p["save_times"] = [r.u64(), r.u64(), 0, 0, 0, 0]
        p["guild_emblem_color"], gv, p["preview_padding"] = r.u8(), r.u8(), r.u16()
        p["experiences"] = [r.u32(), r.u32(), 0, 0, 0, 0]
    p["game_version"] = GAME_VERSION(gv)
    for k in ("left_hand", "right_hand", "torso", "head"):
        p[k] = _preview_item(r)
    p["name"] = r.fixed_string(96 if v >= 104 else 60)
    p["reserved"] = r.u64()
    c["preview"] = {k: p[k] for k in ("save_times", "experiences", "guild_emblem_color", "game_version",
                                      "preview_padding", "left_hand", "right_hand", "torso", "head", "name",
                                      "reserved")}
    c["_flags"], c["_gv"] = flags, gv
    return c


def _quests(r: Reader) -> dict:
    if r.u32() != 0x216F6F57:
        raise ValueError("bad quest section magic")
    q = {"version": r.u32(), "section_size": r.u16()}
    for diff in ("normal", "nightmare", "hell"):
        q[diff] = {f"act{i + 1}": {name: QUEST_FLAGS(r.u16()) for name in names.split()}
                   for i, names in enumerate(QUEST_ACTS)}
    return q


def _waypoints(r: Reader) -> dict:
    if r.u16() != 0x5357:
        raise ValueError("bad waypoint section magic")
    w = {"version": r.u32(), "section_size": r.u16()}
    for diff in ("normal", "nightmare", "hell"):
        d = {"version": r.u16()}
        for i, (n, fmt) in enumerate(WP_ACTS):
            d[f"act{i + 1}"] = fmt(r.bits(n))
        d["extra_waypoint_bits"] = r.bits(9)
        d["extra_waypoint_bytes"], d["reserved"] = r.array(8), r.array(8)
        w[diff] = d
    return w


def _intro(r: Reader) -> dict:
    header = r.u16()
    if header != 0x7701:
        raise ValueError("bad player intro magic")
    size = r.u16()
    if size != 52:
        raise ValueError(f"bad player intro size {size}")
    quest = [r.array(8) for _ in range(3)]
    npc = [r.array(8) for _ in range(3)]
    out = {"header": header, "section_size": size}
    for i, diff in enumerate(("normal", "nightmare", "hell")):
        out[diff] = {"quest_intro_flags": quest[i], "npc_intro_flags": npc[i]}
    return out


def _player_stats(r: Reader, t: Tables) -> list[dict]:
    if r.u16() != 0x6667:
        raise ValueError("bad stats magic")
    out = []
    while True:
        sid = r.bits(9)
        if sid == TERMINATOR:
            break
        cb, cp, cs, *_ = t.stat(sid)
        layer = r.signed(cp) if cp > 0 else 0
        val = r.signed(cb) if cb < 32 and cs else r.bits(cb)
        out.append({"id": sid, "layer": layer, "value": val})
    r.align()
    return out


def _demon(r: Reader, t: Tables, v: int):
    if v < 103 or r.remaining() < 48:
        return None
    start = r.pos
    version, magic = r.u16(), r.u16()
    if magic != 0x666C or version != 1:
        r.pos = start
        return None
    has = r.u8() != 0
    out = {"section_version": version, "has_demon": has, "padding": r.u8(), "demon": None}
    if has:
        size = r.u16()
        d = {"demon_type": DEMON_TYPE(r.u16()), "class_id": (r.u16() - 1) & 0xFFFF, "name_seed": r.u16(),
             "mon_flags": r.u16(), "num_stats": r.u16(), "difficulty": DIFFICULTY(r.u8()),
             "game_version": GAME_VERSION(r.u8()), "padding_0e": r.u16(), "is_ladder": r.u32(), "game_type": r.u8(),
             "padding_15": r.array(3), "level_id": r.u32(), "monster_level": r.u8(), "is_terrorized": r.u8(),
             "padding_1e": r.u16(), "terror_zone_param": r.u32(), "level_bonus": r.u32(),
             "bonus_damage_percent": r.u32()}
        for k in ("player_count_hp_bonus", "player_count_experience_bonus", "player_count_skill_bonus",
                  "player_count_difficulty", "player_count"):
            d[k] = _i32(r.u32())
        d["components"], d["mon_umod"], d["padding_59"] = r.array(16), r.array(9), r.array(3)
        d["stats"] = []
        if size:
            br = Reader(r.raw(size))
            if br.u16() != 0x6667:
                raise ValueError("bad demon stats magic")
            while (sid := br.bits(9)) != TERMINATOR:
                cp = t.stat(sid)[1]
                layer = br.signed(cp) if cp > 0 else 0
                d["stats"].append({"id": sid, "layer": layer, "value": br.u32()})
        out["demon"] = d
    return out


def parse_d2s(data: bytes, t: Tables) -> dict:
    r = Reader(data)
    if r.u32() != 0xAA55AA55:
        raise ValueError("not a D2 save file")
    v = r.u32()
    save = {"version": v, "file_size": r.u32(), "checksum": r.u32()}
    ch = _character(r, v)
    flags, gv = ch.pop("_flags"), ch.pop("_gv")
    save["character"] = ch
    save["quests"] = _quests(r)
    save["waypoints"] = _waypoints(r)
    save["player_intro"] = _intro(r)
    save["stats"] = _player_stats(r, t)
    if r.u16() != 0x6669:
        raise ValueError("bad skills magic")
    save["skills"] = {"class": ch["class"], "levels": r.array(ch["num_skills"])}
    save["items"] = read_items(r, t, v)
    if r.u16() != 0x4D4A:
        raise ValueError("bad corpse section magic")
    save["corpses"] = [{"unused": r.u32(), "x": r.u32(), "y": r.u32(), "items": read_items(r, t, v)}
                       for _ in range(r.u16())]
    save["merc_items"] = save["iron_golem"] = save["demon"] = None
    expansion = gv > 1 if v >= 104 else bool(flags & 0x20)
    if expansion:
        if r.u16() != 0x666A:
            raise ValueError("bad merc items magic")
        m = ch["merc"]
        has_merc = bool(m["seed"] or m["name_index"] or m["experience"])
        save["merc_items"] = {"items": read_items(r, t, v) if has_merc else []}
        if r.u16() != 0x666B:
            raise ValueError("bad iron golem magic")
        save["iron_golem"] = {"golem_item": read_item(r, t, v) if r.u8() else None}
        if gv == 3:
            save["demon"] = _demon(r, t, v)
    rest = r.remaining() >> 3
    save["trailing_data"] = list(r.raw(rest)) if rest else []
    return save


# --- shared stash ------------------------------------------------------------------------------------------------

def _chronicle(r: Reader, body: int) -> dict:
    start = r.pos >> 3
    if r.u32() != 0xC0EAEDC0:
        raise ValueError("bad chronicle magic")
    c = {"version": r.u16()}
    counts = (r.u16(), r.u16(), r.u16())
    c["reserved"] = r.array(8)
    for k, n in zip(("set_entries", "unique_entries", "runeword_entries"), counts):
        c[k] = [{"item_id": r.u32(), "source": r.u16(), "timestamp": r.u32()} for _ in range(n)]
    trailing = body - ((r.pos >> 3) - start)
    c["trailing_data"] = list(r.raw(trailing)) if trailing > 0 else []
    return {k: c[k] for k in ("version", "set_entries", "unique_entries", "runeword_entries", "reserved",
                              "trailing_data")}


def parse_d2i(data: bytes, t: Tables) -> list[dict]:
    r, tabs = Reader(data), []
    while r.remaining() > 64 * 8:
        start = r.pos >> 3
        if r.u32() != 0xAA55AA55:
            raise ValueError("bad stash tab magic")
        tab = {"stash_format": r.u32(), "save_version": r.u32(), "gold": r.u32()}
        size = r.u16()
        tab["season"] = r.u16()
        tt = r.u8()
        tab["padding_21"], tab["withdraw_only_data"], tab["padding_44"] = r.array(3), r.array(20), r.array(20)
        if tab["stash_format"] < 2:
            tt = 0
        tab["tab_type"] = TAB_TYPE(tt)
        tab["items"], tab["chronicle"] = [], None
        if tt == 2:
            tab["chronicle"] = _chronicle(r, size - 64)
        else:
            tab["items"] = read_items(r, t, tab["save_version"])
        if size == 0:
            raise ValueError("stash tab size is zero")
        r.pos = (start + size) * 8
        tabs.append(tab)
    return tabs


# --- convenience -------------------------------------------------------------------------------------------------

_TABLES: dict[Path, Tables] = {}


def tables(txt_dir: Path | None = None) -> Tables:
    """Tables from txt105/ (default: armory/work/txt105). Missing game tables (txt105/ and xl/, which bot/gear.py
    reads) are extracted from the tracked armory bundle."""
    if txt_dir is None:
        from .config import ROOT

        work = ROOT / "armory" / "work"
        txt_dir = work / "txt105"
        if not (txt_dir / "itemstatcost.txt").exists() or not (work / "xl").exists():
            import tarfile

            work.mkdir(parents=True, exist_ok=True)
            with tarfile.open(ROOT / "armory" / "scanbundle.tgz") as tf:
                tf.extractall(work, members=[m for m in tf.getmembers() if m.name.lstrip("./").split("/")[0] in ("txt105", "xl")], filter="data")
    if txt_dir not in _TABLES:
        _TABLES[txt_dir] = Tables(txt_dir)
    return _TABLES[txt_dir]


def read_d2s(path: Path, t: Tables | None = None) -> dict:
    return parse_d2s(Path(path).read_bytes(), t or tables())


def read_d2i(path: Path, t: Tables | None = None) -> list[dict]:
    return parse_d2i(Path(path).read_bytes(), t or tables())


if __name__ == "__main__":  # same interface as d2dump: `python -m bot.d2save c|s <file>` prints JSON
    import json
    import sys

    mode, file = sys.argv[1], sys.argv[2]
    print(json.dumps(read_d2s(Path(file)) if mode == "c" else read_d2i(Path(file)), separators=(",", ":")))
