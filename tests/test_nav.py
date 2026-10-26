"""Odometry jump detection and bonfire re-anchoring on synthetic frames."""
from types import SimpleNamespace

import cv2
import numpy as np

from bot.io.fake import FakeCapture
from bot.nav import Odometer, anchor_bonfire, find_fires

RNG = np.random.default_rng(0)
WORLD = cv2.GaussianBlur(RNG.integers(0, 255, (3000, 4000, 3), dtype=np.uint8), (7, 7), 0)


def view(wx: int, wy: int, fires=()) -> np.ndarray:
    """1280x720 view of WORLD with the camera at world offset (wx, wy); fires = [(sx, sy, r)]."""
    f = WORLD[1000 + wy : 1720 + wy, 1000 + wx : 2280 + wx].copy()
    for sx, sy, r in fires:
        cv2.circle(f, (sx, sy), r, (40, 160, 255), -1)  # saturated orange
    return f


def test_odometer_tracks_hops():
    odo = Odometer(view(0, 0))
    odo.update(view(200, 0))
    odo.update(view(350, 150))
    assert np.allclose(odo.pos, (350, 150), atol=4)
    assert not odo.lost


def test_odometer_flags_jump():
    odo = Odometer(view(0, 0))
    odo.update(view(900, 500))  # far beyond a hop: no usable overlap
    assert odo.lost


def test_find_fires_sizes():
    fires = find_fires(view(0, 0, [(900, 400, 20), (300, 200, 6)]))
    assert fires[0][2] > 1000 and abs(fires[0][0] - 900) < 3
    assert fires[1][2] < 300  # torch-sized


def test_anchor_bonfire_corrects_drift():
    # Bonfire at world (500, 100); camera really at (0, 0) so it shows at screen (1140, 430).
    frame = view(0, 0, [(1140, 430, 20), (700, 200, 6)])
    odo = Odometer(frame)
    odo.pos = np.array([60.0, -40.0])  # drifted
    odo.lost = True
    bot = SimpleNamespace(capture=FakeCapture([frame]))
    assert anchor_bonfire(bot, odo, (500, 100))
    assert np.allclose(odo.pos, (0, 0), atol=3)
    assert not odo.lost


def test_anchor_bonfire_none_in_view():
    frame = view(0, 0, [(700, 200, 6)])  # only a torch
    odo = Odometer(frame)
    odo.pos = np.array([10.0, 10.0])
    bot = SimpleNamespace(capture=FakeCapture([frame]), save_failure=lambda note: None)
    assert not anchor_bonfire(bot, odo, (500, 100))
    assert np.allclose(odo.pos, (10, 10), atol=3)
