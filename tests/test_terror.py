"""LK's Terror Zone banner ("Terrorized" under "Entering Lower Kurast", 2026-11-02 10:14)."""
from pathlib import Path

import cv2

from bot.lk import terrorized

F = Path(__file__).resolve().parent.parent / "fixtures" / "terror"


def test_terrorized_banner():
    assert terrorized(cv2.imread(str(F / "lk_terrorized.png")))


def test_normal_lk():
    assert not terrorized(cv2.imread(str(F / "lk_normal.png")))
