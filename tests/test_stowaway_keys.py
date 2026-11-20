"""2026-11-19/20: four key stacks went to shared page 1. The scan's frame came before the inventory panel was drawn
(0 empty cells, everything "loot"), so the key stack was Ctrl+clicked with the loot."""
from pathlib import Path

import cv2
import numpy as np

from bot import town
from bot.vision.inventory import is_key

F = Path(__file__).parent.parent / "fixtures"
TPL = cv2.imread(str(town.ASSETS / "inv_key.png"))


def full(crop):  # logs/loot tooltips keep x 400..1280
    f = np.zeros((crop.shape[0], 1280, 3), np.uint8)
    f[:, 400:] = crop
    return f


def test_hover_frame_shows_the_key_stack():
    f = full(cv2.imread(str(F / "stowaway" / "key_tooltip_20261120.png")))
    assert is_key(f, 3, 2, TPL)
    assert not is_key(f, 4, 3, TPL)  # a small charm


class FakeBot:
    def __init__(self, frames):
        self.frames, self._templates = list(frames), {}
        self.cfg = {"inventory": {"protected": [[4, 0, 6, 4], [3, 3, 1, 1]]}}
        self.input = type("I", (), {"move": lambda *a: None})()
        self.kill = type("K", (), {"sleep": lambda *a: None})()

    @property
    def capture(self):
        bot = self

        class C:
            def grab(self):
                return bot.frames.pop(0) if len(bot.frames) > 1 else bot.frames[0]
        return C()


def test_scan_waits_for_the_inventory_panel():
    opened = cv2.imread(str(F / "inventory" / "keys8_hel.png"))
    closed = cv2.imread(str(F / "labeled" / "in_game" / "town_20261025-154438.png"))
    inv = town._scan_inventory(FakeBot([closed, closed, opened]), wait_open=True)
    assert inv["empty"] or inv["key"]  # read from the open panel, not the world behind it
    stale = town._scan_inventory(FakeBot([closed]))
    assert not stale["empty"]  # what the bad scans saw
