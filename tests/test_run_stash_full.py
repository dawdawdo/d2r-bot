"""A full stash during the LK fallback: only runes are picked, so the session can go on."""
from bot.run import runes_only


def test_full_stash_narrows_pickup_to_runes_once():
    cfg = {"loot": {"pick": ["rune", "unique", "set", "magic"], "pick_white_other": True}}
    assert runes_only(cfg) is True
    assert cfg["loot"]["pick"] == ["rune"] and cfg["loot"]["pick_white_other"] is False
    assert runes_only(cfg) is False
