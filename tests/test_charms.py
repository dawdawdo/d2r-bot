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
    assert charms.describe(item("cm3", 0, 0, [(188, 57, 1)])) == "Grand Charm: +1 Warlock tab 2 skills"


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
    assert {c: k["what"] for c, k in kept.items()} == {(1, 0): "Small Charm: 5 all res"}


def test_sort_drops_nothing_when_the_save_is_older_than_the_inventory():
    save = {"items": [item("cm3", 0, 0, [(7, 0, 5 << 8)])]}
    junk, kept = charms.sort(save, [(0, 0), (0, 1), (0, 2), (4, 1)], RULES)  # (4, 1): picked up after the save
    assert junk == [] and (0, 0) in kept
    junk, _ = charms.sort(save, [(0, 0), (0, 1)], RULES)  # the charm reaches a cell that isn't loot
    assert junk == []




def _bot(cfg=None):
    from bot.killswitch import KillSwitch
    kill = KillSwitch()
    kill.sleep = lambda s: kill.check()
    b = type("B", (), {})()
    b.cfg, b.kill, b.frame = cfg or {"hotkeys": {"inventory": "i"}}, kill, None
    b.press = lambda *a: None
    b.save_failure = lambda note: None
    return b


def _drop_setup(monkeypatch, frames):
    from bot import town
    seq = list(frames)
    monkeypatch.setattr(town, "close_stash", lambda bot: True)
    monkeypatch.setattr(town, "stash_shown", lambda bot: False)
    monkeypatch.setattr(town, "_ctrl_click", lambda bot, x, y: clicks.append((x, y)))
    monkeypatch.setattr(town, "_occupied", lambda bot: seq.pop(0))
    clicks = []
    return town, clicks


def test_drop_that_takes_another_item_stops_with_the_game_open(monkeypatch):
    """2026-11-28: clicks on (0,0), (3,0), (3,2) dropped (6,0), (9,0) and the cube at (8,2) instead."""
    import pytest

    from bot.killswitch import KillSwitchTripped
    town, clicks = _drop_setup(monkeypatch, [{(3, 2), (8, 2), (9, 2), (8, 3), (9, 3)}, {(3, 2), (8, 3), (9, 3)}])
    bot = _bot()
    with pytest.raises(KillSwitchTripped):
        town.drop_cells(bot, [(3, 2)], "spare key stacks")
    assert bot.drops_off and bot.kill.kind == "f12" and len(clicks) == 1


def test_drop_checks_each_click(monkeypatch):
    town, clicks = _drop_setup(monkeypatch, [{(0, 0), (1, 0), (5, 0)}, {(1, 0), (5, 0)}, {(5, 0)}])
    bot = _bot()
    assert town.drop_cells(bot, [(0, 0), (1, 0)], "spare key stacks") == 2 and not getattr(bot, "drops_off", False)


def test_a_drop_that_takes_nothing_turns_drops_off(monkeypatch):
    town, clicks = _drop_setup(monkeypatch, [{(0, 0), (5, 0)}, {(0, 0), (5, 0)}])
    bot = _bot()
    assert town.drop_cells(bot, [(0, 0), (1, 1)], "spare rejuvs") == 0 and bot.drops_off and len(clicks) == 1
    assert town.drop_cells(bot, [(0, 0)], "spare rejuvs") == 0 and len(clicks) == 1  # off for the session


def test_missing_own_item_stops_the_session():
    import pytest

    from bot import town
    from bot.killswitch import KillSwitchTripped
    cube, tome = item("box", 8, 2), item("tbk", 9, 0)
    bot = _bot({"inventory": {"own_items": [["box", 8, 2], ["tbk", 9, 0]]}})
    town.check_own_items(bot, {"items": [cube, tome]})  # all there
    with pytest.raises(KillSwitchTripped):
        town.check_own_items(bot, {"items": [tome]})
    assert "box" in bot.kill.reason
