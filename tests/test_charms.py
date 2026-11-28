import struct

from bot import charms

RULES = {"small": {"all_res": 1}, "large": {"all_res": 1}, "grand": {"all_res": 1, "skills": 1}}


def item(code, c, r, stats=(), quality="Magic", page="Inventory"):
    return {"code": struct.unpack("<I", code.ljust(4).encode())[0], "quality": quality,
            "position": {"mode": "Stored", "store_page": page, "inv_x": c, "inv_y": r},
            "stats": [{"id": i, "layer": layer, "value": v} for i, layer, v in stats]}


ALL_RES = [(39, 0, 5), (41, 0, 5), (43, 0, 5), (45, 0, 5)]


def test_keep_rules():
    assert charms.keep(item("cm3", 0, 0, [(188, 50, 1), (7, 0, 16 << 8)]), RULES)  # a skiller, any class
    assert not charms.keep(item("cm3", 0, 0, [(7, 0, 40 << 8)]), RULES)
    assert charms.keep(item("cm3", 0, 0, [(39, 0, 13), (41, 0, 13), (43, 0, 13), (45, 0, 13)]), RULES)
    assert charms.keep(item("cm1", 0, 0, ALL_RES), RULES)
    assert not charms.keep(item("cm1", 0, 0, [(43, 0, 9), (0, 0, 2)]), RULES)  # one resist isn't all res
    assert not charms.keep(item("cm2", 0, 0, [(80, 0, 6)]), RULES)
    assert charms.keep(item("cm1", 0, 0, [(7, 0, 20 << 8)], quality="Unique"), RULES)  # Annihilus and friends


def test_describe():
    gc = item("cm3", 0, 0, [(188, 50, 1), (7, 0, 16 << 8)])
    assert charms.describe(gc) == "Grand Charm: +1 Martial Arts skills; +16 life"
    assert charms.describe(item("cm1", 0, 0, ALL_RES + [(80, 0, 7)])) == "Small Charm: 5 all res; 7% MF"


def test_sort_drops_junk_loot_charms_only():
    save = {"items": [
        item("cm3", 5, 0, [(7, 0, 5 << 8)]),          # Stephen's own (protected: not a loot cell)
        item("cm3", 0, 0, [(7, 0, 5 << 8)]),          # loot junk, cells (0, 0)..(0, 2)
        item("cm1", 1, 0, ALL_RES),                   # loot keeper
        item("cm1", 2, 0, [(19, 0, 30)], page="Stash"),  # same cell in the stash: not inventory
        item("rin", 3, 0, [], quality="Unique"),
    ]}
    junk, kept = charms.sort(save, [(0, 0), (0, 1), (0, 2), (1, 0), (3, 0)], RULES)
    assert [j["cell"] for j in junk] == [(0, 0)] and junk[0]["cells"] == {(0, 0), (0, 1), (0, 2)}
    assert kept == {(1, 0): "Small Charm: 5 all res"}


def test_sort_drops_nothing_when_the_save_is_older_than_the_inventory():
    save = {"items": [item("cm3", 0, 0, [(7, 0, 5 << 8)])]}
    junk, kept = charms.sort(save, [(0, 0), (0, 1), (0, 2), (4, 1)], RULES)  # (4, 1): picked up after the save
    assert junk == [] and (0, 0) in kept
    junk, _ = charms.sort(save, [(0, 0), (0, 1)], RULES)  # the charm reaches a cell that isn't loot
    assert junk == []


def test_stash_stop_drops_junk_and_keeps_the_rest(monkeypatch):
    from bot import town

    save = {"items": [item("cm3", 0, 0, [(7, 0, 5 << 8)]), item("cm1", 1, 0, ALL_RES), item("cm1", 2, 0, [(19, 0, 9)])]}
    monkeypatch.setattr(charms, "read_save", lambda cfg: save)
    monkeypatch.setattr(town, "_save_tooltip", lambda bot, x, y: (x, y))
    monkeypatch.setattr(town, "_is_charm", lambda tip, x, y: tip == (x, y) and x < 940)  # (2, 0) "isn't" a charm
    monkeypatch.setattr(town, "_log_loot", lambda items: logged.extend(items))
    monkeypatch.setattr(town, "drop_cells", lambda bot, cells, what: dropped.extend(cells) or len(cells))
    logged, dropped = [], []
    bot = type("B", (), {"cfg": {"loot": {"charms_keep": RULES}, "hotkeys": {"inventory": "i"}},
                         "press": lambda *a: None, "kill": type("K", (), {"sleep": lambda *a: None})()})()
    inv = {"other": [(0, 0), (0, 1), (0, 2), (1, 0), (2, 0)]}
    n, kept = town._drop_junk_charms(bot, inv)
    assert n == 3 and dropped == [(0, 0)] and logged == ["Charm dropped: Grand Charm: +5 life"]
    assert inv["other"] == [(1, 0), (2, 0)]
    assert kept == {(1, 0): "Small Charm: 5 all res", (2, 0): "Small Charm: +9 AR"}  # (2, 0) didn't say Charm
