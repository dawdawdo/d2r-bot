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


def test_open_plateau_steps_by_screen_odometry():
    """Smoked's Worldstone Keep 2 waypoint (2026-11-27): a lit plateau with almost no automap lines outside his light.
    The first hop (-264, -17) was "lost"; the screen moved (-268, -38) at resp 0.48."""
    import cv2
    import numpy as np

    from bot.durance import AutomapOdometer, use_style

    fix = Path(__file__).resolve().parent.parent / "fixtures" / "durance"
    before, after = (cv2.imread(str(fix / f"keep_plateau_{n}.png")) for n in ("before", "after"))
    use_style("keep")
    try:
        odo = AutomapOdometer(before)
        dx, dy = odo.update(after, expect=(-264, -17))
        assert not odo.lost and odo.scene_run == 1
        assert -300 < dx < -240 and -60 < dy < -15
        assert odo.added == 2  # the view went onto the canvas
        lost = AutomapOdometer(before)
        lost.lost = True  # already lost: its position is stale, no screen step from it
        lost.update(after, expect=(-264, -17))
        assert lost.lost
    finally:
        use_style("tan")
