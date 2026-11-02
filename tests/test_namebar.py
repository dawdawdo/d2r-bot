"""Name bar reader on Stephen's Meph kill recording (view 120: Mephisto hovered, bar part red)."""
from pathlib import Path

import cv2
import pytest

from bot.vision.namebar import BAR, _red, name_bar

VIEW = Path(__file__).resolve().parent.parent / "maps/blizzaga_hell/durance3_route_20261101-171245/views/120.jpg"
pytestmark = pytest.mark.skipif(not VIEW.exists(), reason="recording not present")


def test_mephisto_bar_reads_life():
    nb = name_bar(cv2.imread(str(VIEW)))
    assert nb and nb["mephisto"] and 0 < nb["life"] <= 1


def test_mephisto_empty_bar_is_dead():
    f = cv2.imread(str(VIEW))
    x, y, w, h = BAR
    strip = f[y : y + h, x : x + w]
    strip[_red(strip)] = (12, 12, 14)  # the box with no life left: dark behind the name
    assert name_bar(f) == {"life": 0.0, "mephisto": True}


def test_no_bar():
    f = cv2.imread(str(VIEW))
    x, y, w, h = BAR
    f[y : y + h, x : x + w] = (10, 10, 10)
    assert name_bar(f) is None
