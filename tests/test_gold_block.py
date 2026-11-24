"""LK gold blocks for merc tasks (supplies.gold_block / gold_total)."""
from bot import supplies

CFG = {"town": {"merc_revive_gold": 50000, "gold_block_until": 500000},
       "paths": {"save_dir": "/nowhere"}, "game": {"character": "Blizzaga"}}


def test_enough_gold_runs_the_task():
    assert supplies.gold_block({}, 120000, CFG) == (False, {})


def test_below_one_revive_starts_a_block_even_with_the_merc_alive():
    lk, st = supplies.gold_block({}, 34163, CFG)
    assert lk and st["gold_block"]


def test_block_lasts_until_the_target():
    st = {"gold_block": True}
    assert supplies.gold_block(st, 60000, CFG) == (True, st)  # one revive's worth is not the end of it
    assert supplies.gold_block(st, None, CFG) == (True, st)  # unreadable save: keep going


def test_block_ends_at_the_target_and_clears_the_no_gold_flag():
    lk, st = supplies.gold_block({"gold_block": True, "stash_gold_empty": True}, 512000, CFG)
    assert not lk and st == {"gold_block": False, "stash_gold_empty": False}


def test_unknown_gold_falls_back_to_the_failed_revive_flag():
    assert supplies.gold_block({"stash_gold_empty": True}, None, CFG)[0]
    assert supplies.gold_block({}, None, CFG) == (False, {})


def test_known_gold_beats_a_stale_flag():
    assert supplies.gold_block({"stash_gold_empty": True}, 300000, CFG)[0] is False


def test_gold_total_adds_carried_stash_and_shared(monkeypatch):
    from bot import d2save

    monkeypatch.setattr(supplies, "_TABLES", object())
    monkeypatch.setattr(d2save, "read_d2s", lambda p, t: {"stats": [{"id": 14, "value": 23654},
                                                                    {"id": 15, "value": 18}, {"id": 0, "value": 9}]})
    monkeypatch.setattr(d2save, "read_d2i", lambda p, t: [{"gold": 38199, "items": []}, {"gold": 0}, {}])
    assert supplies.gold_total(CFG) == 23654 + 18 + 38199


def test_gold_total_unreadable_is_none(monkeypatch):
    from bot import d2save

    monkeypatch.setattr(supplies, "_TABLES", object())

    def boom(p, t):
        raise ValueError("short read")

    monkeypatch.setattr(d2save, "read_d2s", boom)
    assert supplies.gold_total(CFG) is None
