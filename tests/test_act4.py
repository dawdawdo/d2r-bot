"""Act 4 starts: spawn act detection, the LK waypoint seen from the arrival spot, when to end in Act 4."""
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from bot.config import ROOT, load_config
from bot.controller import Controller
from bot.io.fake import FakeCapture, FakeInput, FakeWindow
from bot.killswitch import KillSwitch
from bot.lk import WP_CLICK, _find_lk_wp, load_route
from bot.tasks.lk import town_due
from bot.town import spawn_act
from bot.vision.screen import ScreenClassifier

A4_SPAWN = ROOT / "fixtures" / "labeled" / "in_game" / "a4_spawn_20261027-192316.png"
A3_TOWN = ROOT / "fixtures" / "labeled" / "in_game" / "town_20261025-154438.png"
LK_ARRIVAL = ROOT / "fixtures" / "raw" / "lk_arrival_20261025-172522.png"


@pytest.fixture
def cfg(tmp_path):
    c = load_config()
    c["paths"]["failures"] = tmp_path / "failures"
    return c


def _bot(cfg, frame):
    return Controller(FakeWindow(), FakeCapture([frame]), FakeInput(),
                      ScreenClassifier.from_config(cfg["vision"]["states"]), KillSwitch(), cfg)


def test_spawn_act(cfg):
    assert spawn_act(_bot(cfg, cv2.imread(str(A4_SPAWN)))) == 4
    assert spawn_act(_bot(cfg, cv2.imread(str(A3_TOWN)))) == 3


@pytest.mark.skipif(not LK_ARRIVAL.exists(), reason="raw fixture not in this checkout")
@pytest.mark.parametrize("shift", [(0, 0), (-60, 40), (50, -45)])
def test_lk_wp_found_near_the_arrival_spot(cfg, shift):
    """Back at the WP within the teleport tolerance (60 px): the click lands on the platform."""
    f = cv2.imread(str(LK_ARRIVAL))
    dx, dy = shift
    f = cv2.warpAffine(f, np.float32([[1, 0, dx], [0, 1, dy]]), (f.shape[1], f.shape[0]))
    loc = _find_lk_wp(_bot(cfg, f), load_route(cfg["game"]["route"]))
    assert loc is not None
    x, y = loc[0] + WP_CLICK[0], loc[1] + WP_CLICK[1]
    assert abs(x - (640 + dx)) < 25 and abs(y - (372 + dy)) < 25


def test_lk_wp_not_found_in_town(cfg):
    assert _find_lk_wp(_bot(cfg, cv2.imread(str(A3_TOWN))), load_route(cfg["game"]["route"])) is None


def _b(keys_left=10, keys_used=0, repair_next=False):
    return SimpleNamespace(cfg=load_config(), keys_left=keys_left, keys_used=keys_used, repair_next=repair_next)


def test_town_due():
    assert not town_due(_b(), {"picked": ["rejuv"]})
    assert not town_due(_b(), {"picked": ["key", "rejuv"]})  # extra key stacks: dropped at the A4 spawn
    assert town_due(_b(), {"picked": ["rune"]})         # stash
    assert town_due(_b(keys_left=5, keys_used=2), {})   # keys to buy
    assert town_due(_b(keys_left=None), {})
    assert town_due(_b(repair_next=True), {})
