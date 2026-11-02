"""Ormus by his sprite (templates from Botty, MIT): found where he stands, nothing where he isn't."""
from pathlib import Path

import cv2

from bot.town import ORMUS_SPRITE_MIN, _sprite_hits

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "ormus"
NAMES = [f"ormus_{i}.png" for i in range(6)]


def hits(name):
    return _sprite_hits(cv2.imread(str(FIX / name)), NAMES, (0, 0, 1280, 560), ORMUS_SPRITE_MIN)


def test_found_where_he_stands():
    for name, (x, y) in (("ormus_visible.png", (908, 484)), ("ormus_visible2.png", (892, 420))):
        h = hits(name)
        assert h and abs(h[0][0] - x) < 15 and abs(h[0][1] - y) < 15, (name, h)


def test_nothing_when_absent():
    assert hits("ormus_absent.png") == []
