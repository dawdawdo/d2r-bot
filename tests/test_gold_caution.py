"""Gold picks stop when she's taking damage (2026-11-20: chest gold took chickens from ~4 % to ~25 %)."""
from types import SimpleNamespace

from bot.config import load_config
from bot.lk import under_attack

CFG = load_config()


def bot(hp, mp):
    return SimpleNamespace(cfg=CFG, hp=hp, mp=mp)


def test_calm_keeps_picking():
    assert not under_attack(bot(100, 80), 100, 78)


def test_life_or_shield_loss_stops():
    assert under_attack(bot(94, 80), 100, 80)  # life dropped 6
    assert under_attack(bot(89, 80), 89, 80)   # below 90
    assert under_attack(bot(100, 60), 100, 75)  # energy shield ate 15 mana


def test_no_reading_never_stops():
    assert not under_attack(SimpleNamespace(cfg=CFG), None, None)
