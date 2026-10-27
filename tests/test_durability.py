from pathlib import Path

import cv2
import numpy as np
import pytest

from bot.vision.durability import _tpl, durability_full

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "durability"


@pytest.mark.parametrize("p", sorted(FIX.glob("*.png")), ids=lambda p: p.stem)
def test_full_items(p):
    assert durability_full(cv2.imread(str(p))) is True  # just repaired, 2026-10-27


def _right_number_x(frame):
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    word, of = _tpl("tt_durability.png"), _tpl("tt_of.png")
    _, _, _, (x, y) = cv2.minMaxLoc(cv2.matchTemplate(g, word, cv2.TM_CCOEFF_NORMED))
    line = g[y : y + word.shape[0], x + word.shape[1] : x + word.shape[1] + 150]
    _, _, _, (ox, _) = cv2.minMaxLoc(cv2.matchTemplate(line, of, cv2.TM_CCOEFF_NORMED))
    return x + word.shape[1] + ox + of.shape[1] + 3, y, word.shape[0]


def test_lower_durability_is_not_full():
    viper = cv2.imread(str(FIX / "dur_1055_225_20261027-014312.png"))   # 24 of 24
    shako = cv2.imread(str(FIX / "dur_1055_105_20261027-014313.png"))   # 12 of 12
    vx, vy, h = _right_number_x(viper)
    sx, sy, _ = _right_number_x(shako)
    viper[vy : vy + h, vx : vx + 30] = 0
    viper[vy : vy + h, vx : vx + 20] = shako[sy : sy + h, sx : sx + 20]  # "24 of 12"
    assert durability_full(viper) is False


def test_no_tooltip():
    assert durability_full(np.zeros((720, 1280, 3), np.uint8)) is None


def test_key_stack_full():
    f = cv2.imread(str(FIX.parent / "inventory" / "key_tooltip_12of12.png"))
    assert durability_full(f, "tt_quantity.png") is True
    assert durability_full(f) is None  # keys have no durability line


def test_key_stack_not_full():
    f = cv2.imread(str(FIX.parent / "inventory" / "key_tooltip_8of12.png"))
    assert durability_full(f, "tt_quantity.png") is False
