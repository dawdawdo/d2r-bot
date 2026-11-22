"""bot/bases.py: new armor / weapon bases between two save backups."""
from bot import bases, d2save


def _item(code, quality="Normal", seed=1, mode="Stored", rw=None, flags="IDENTIFIED", sockets=0):
    return {"code": d2save.code_int(code), "seed": seed, "quality": quality, "runeword_id": rw, "flags": flags,
            "position": {"mode": mode}, "sockets": [None] * sockets, "level": 79, "defense": 400}


def test_only_stored_white_or_superior_gear_counts():
    items = [_item("xla", sockets=4, flags="IDENTIFIED | ETHEREAL"),  # Demonhide Armor, eth, 4 os
             _item("utp", "Superior", seed=2),                          # Archon Plate, superior
             _item("utp", "Magic", seed=3),                             # magic: not a base
             _item("utp", seed=4, rw=20537),                            # a runeword
             _item("utp", seed=5, mode="Equipped"),                     # worn
             _item("gpw", seed=6),                                      # a gem
             _item("7fb", seed=7)]                                      # Colossus Sword: weapon base
    found = bases.bases_in(items, "shared tab 1")
    assert [(b["code"], b["kind"]) for b in found] == [("xla", "armor"), ("utp", "armor"), ("7fb", "weapon")]
    assert found[0]["eth"] and found[0]["sockets"] == 4
    assert bases.base_name("utp") == "Archon Plate"
    assert "4 os" in bases.describe(found[0]) and "ethereal" in bases.describe(found[0])
