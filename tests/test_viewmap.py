"""Lut Gholein view map (maps/towns/a2): where a view is, and no false fixes from repeated sprites."""
from pathlib import Path

import cv2
import pytest

from bot.vision.viewmap import ViewMap

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures" / "townmap"


@pytest.fixture(scope="module")
def a2():
    return ViewMap.load(ROOT / "maps" / "towns" / "a2")


def test_map_has_waypoint(a2):
    assert "wp" in a2.targets and len(a2.frames) >= 9


def test_locates_east_of_the_obelisk(a2):
    # the old click walk's failure frame (2026-11-02): ~1000 px east of the waypoint
    pos, cells = a2.locate(cv2.imread(str(FIX / "a2_east.png")))
    assert abs(pos[0] - 825) < 40 and abs(pos[1] + 855) < 40 and cells >= 20


def test_keyframes_locate_on_themselves(a2):
    for kf in a2.frames[:5]:
        pos, _ = a2.locate(cv2.imread(str(a2.root / kf["file"])))
        assert abs(pos[0] - kf["x"]) < 15 and abs(pos[1] - kf["y"]) < 15


def test_other_town_is_not_located(a2):
    frames = sorted((ROOT / "fixtures" / "labeled" / "in_game").glob("*.png"))[:6]  # Act 3 / LK views
    assert frames
    for f in frames:
        assert a2.locate(cv2.imread(str(f))) is None, f.name
