"""Bot page "Current gear" totals (bot/gear.py) on a synthetic character; tables from the armory bundle."""
import struct
from pathlib import Path

import pytest

from bot import gear

WORK = Path(__file__).resolve().parent.parent / "armory" / "work"


def _it(code, loc, stats=(), sockets=(), mode="Equipped", page="Null"):
    c = lambda s: struct.unpack("<I", s.ljust(4).encode())[0]  # noqa: E731
    return {"code": c(code), "position": {"mode": mode, "body_location": loc, "store_page": page},
            "stats": [{"id": i, "layer": l, "value": v} for i, l, v in stats], "runeword_stats": None,
            "sockets": [{"code": c(s), "stats": []} for s in sockets]}


@pytest.fixture(scope="module")
def tables():
    if not (WORK / "xl" / "gems.txt").exists():
        pytest.skip("armory/work not built (python -m bot.armory --no-upload)")
    return gear.Tables(WORK)


def test_totals_count_sockets_by_slot_and_skip_weapon_swap(tables):
    d = {"character": {"class": "Sorceress", "level": 91, "name": "X"},
         "quests": {k: {"act5": {"prison_of_ice": "REWARD_GRANTED"}} for k in ("normal", "nightmare", "hell")},
         "stats": [{"id": 0, "value": 156}, {"id": 7, "value": 190 * 256}],
         "items": [_it("uap", "Head", [(80, 0, 50)], ["r24"]),                  # Shako + Ist (helm: +25 MF)
                   _it("obf", "LeftArm", [(80, 0, 50), (105, 0, 20)], ["r24"]),  # orb = weapon: Ist +30 MF
                   _it("uit", "RightArm", [], ["r10"]),                          # Thul in a shield: +35 cold res
                   _it("fla", "RightHand", [(80, 0, 99), (105, 0, 99)]),        # weapon swap: not counted
                   _it("cm3", "None", [(39, 0, 10)], mode="Stored", page="Inventory")]}
    t = gear.totals(d, tables)
    assert t["mf"] == 155 and t["fcr"] == 20 and t["cold"] == 35 and t["fire"] == 10
    s = gear.summary(d, tables)
    res = {r[0]: r[1] for r in s["groups"][0]["rows"]}
    assert res["Cold"] == f"{35 + 30 - 100}%" and res["Fire"] == f"{10 + 30 - 100}%"
