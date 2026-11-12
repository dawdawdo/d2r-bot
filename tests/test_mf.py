"""Magic find from a d2dump character JSON, and the per-task MF gate (bot/mf.py)."""
import struct
from types import SimpleNamespace

from bot.mf import gate, magic_find


def _it(code, mode, loc="None", page="Null", mf=0, rw_mf=0, jewel_mf=0):
    return {"code": struct.unpack("<I", code.ljust(4).encode())[0],
            "position": {"mode": mode, "body_location": loc, "store_page": page},
            "stats": [{"id": 80, "value": mf}] if mf else [{"id": 39, "value": 5}],
            "runeword_stats": [{"id": 80, "value": rw_mf}] if rw_mf else None,
            "sockets": [None, {"stats": [{"id": 80, "value": jewel_mf}]}] if jewel_mf else []}


def test_counts_equipped_and_inventory_charms_only():
    d = {"items": [
        _it("uap", "Equipped", "Head", mf=50),               # Shako
        _it("obf", "Equipped", "LeftArm", mf=50),            # Oculus, main weapon slot
        _it("fla", "Equipped", "RightHand", rw_mf=99),       # weapon swap (Call to Arms): not active
        _it("mgl", "Equipped", "Gloves", mf=10, jewel_mf=9),
        _it("cm1", "Stored", page="Inventory", mf=7),        # small charm in the inventory counts
        _it("cm1", "Stored", page="Stash", mf=7),            # in the stash it doesn't
        _it("rin", "Stored", page="Inventory", mf=30),       # a ring in the inventory isn't worn
    ]}
    total, parts = magic_find(d)
    assert total == 50 + 50 + 19 + 7
    assert ("fla", 99) not in parts


def test_gate_swaps_low_mf_boss_for_nothing_when_unknown():
    cfg = {"mf": {"min": {"meph": 200}}}
    tasks = [SimpleNamespace(name="lk"), SimpleNamespace(name="meph")]
    kept, low = gate(tasks, {"mf": 0}, cfg)
    assert [t.name for t in kept] == ["lk"] and low == ["meph"]
    kept, low = gate(tasks, {"mf": 280}, cfg)
    assert len(kept) == 2 and low == []
    kept, low = gate(tasks, None, cfg)  # unreadable save (Windows: no d2dump): no gate
    assert len(kept) == 2 and low == []
