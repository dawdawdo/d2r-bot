"""The bot must only ever play the configured character (2026-11-04: Play landed on ThroatCutter)."""
import os
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from bot import lifecycle
from bot.killswitch import KillSwitch, KillSwitchTripped

FRAME = Path(__file__).resolve().parent.parent / "fixtures" / "menu" / "char_list_throatcutter_selected.png"


def menu_frame():
    frame = np.zeros((720, 1280, 3), np.uint8)
    frame[40:540, 1030:1250] = cv2.imread(str(FRAME))
    return frame


class Bot:
    def __init__(self, frame, save_dir="", name="Blizzaga"):
        self.cfg = {"game": {"character": name}, "paths": {"save_dir": str(save_dir)}}
        self.capture = type("C", (), {"grab": lambda s: frame})()
        self.kill = KillSwitch()
        self.clicks, self.failures = [], []

    def click(self, x, y):
        self.clicks.append((x, y))

    def save_failure(self, what):
        self.failures.append(what)


def test_finds_blizzaga_row_when_another_character_is_selected():
    x, y = lifecycle.find_character(menu_frame(), "Blizzaga")
    assert 1046 <= x <= 1114 and 134 <= y <= 148


def test_select_clicks_the_row():
    bot = Bot(menu_frame())
    lifecycle.select_character(bot)
    assert len(bot.clicks) == 1 and 134 <= bot.clicks[0][1] <= 148


def test_select_stops_the_session_when_the_name_is_missing():
    bot = Bot(np.zeros((720, 1280, 3), np.uint8))
    with pytest.raises(KillSwitchTripped):
        lifecycle.select_character(bot)
    assert not bot.clicks and bot.kill.tripped


def _saves(tmp_path, newest):
    for i, name in enumerate(["Other", newest]):
        p = tmp_path / f"{name}.d2s"
        p.write_bytes(b"x")
        t = time.time() + i
        os.utime(p, (t, t))


def test_right_character_passes(tmp_path):
    _saves(tmp_path, "Blizzaga")
    bot = Bot(None, tmp_path)
    lifecycle.check_character(bot)
    assert not bot.kill.tripped


def test_wrong_character_leaves_and_stops(tmp_path, monkeypatch):
    _saves(tmp_path, "ThroatCutter")
    left = []
    monkeypatch.setattr(lifecycle, "save_and_exit", lambda b: left.append(b))
    bot = Bot(None, tmp_path)
    with pytest.raises(KillSwitchTripped):
        lifecycle.check_character(bot)
    assert left == [bot] and bot.kill.tripped
