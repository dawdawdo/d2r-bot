from pathlib import Path

import cv2

from bot.vision.inventory import inventory_open

F = Path(__file__).parent.parent / "fixtures"


def test_open_windows_fixture():
    assert inventory_open(cv2.imread(str(F / "inventory" / "keys8_hel.png")))


def test_closed_in_game():
    assert not inventory_open(cv2.imread(str(F / "labeled" / "in_game" / "town_20261025-154438.png")))
