"""Armor Stands (Stephen 2026-11-21: find them and try them). One NE of each camp's west hut, reached after nw_deep."""
from pathlib import Path

import cv2

from bot import lk

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "racks"


def _box(img):
    return (0, 0, img.shape[1], img.shape[0])


def test_stand_and_rack_tooltips_match_and_others_dont():
    for name, want in (("armor_stand_20261121.png", True), ("weapon_rack_20261119.png", True),
                       ("basket_20261121.png", False)):
        img = cv2.imread(str(FIX / name))
        assert lk._is_rack(img, _box(img)) is want, name


def test_nw_deep_targets_carry_the_armor_stand():
    ts = {t["name"]: t for t in lk.bonfire_targets({"name": "east", "world": [1000, 500]})}
    st = ts["east_nw_deep"]["stands_world"][0]
    assert st["at"] == [1000 - 305, 500 - 677] and st["from"] == [1000 - 305, 500 - 567]
    assert "stands_world" not in ts["east_nw"] and "stands_world" not in ts["east_ne"]
