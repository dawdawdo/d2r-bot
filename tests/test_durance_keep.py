"""Worldstone Keep automap ("keep" style, bot/durance.py): the map-open check must not fire on the lit waypoint."""
from pathlib import Path

import cv2

from bot import durance

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "durance"


def test_keep_map_open_is_read_from_the_area_text():
    durance.use_style("keep")
    try:
        assert not durance.automap_shown(cv2.imread(str(FIX / "keep_map_off_lit_wp.png")))  # 5,383 line px, map off
        assert durance.automap_shown(cv2.imread(str(FIX / "keep_throne_map_on.png")))  # 3,646 line px, map on
    finally:
        durance.use_style("tan")
