"""Chest tooltips from GLaDOS (Linux/Proton, 2026-11-08): the box touches near-black scenery and its
Large Font letters are thick. Crops are 400x180 around the hover point, which sits at (200, 120)."""
from pathlib import Path

import cv2
import pytest

from bot.lk import _is_chest
from bot.vision.tooltip import find_tooltip

FRAMES = sorted((Path(__file__).resolve().parent.parent / "fixtures" / "tooltips_linux").glob("*.png"))


@pytest.mark.parametrize("path", FRAMES, ids=[p.stem for p in FRAMES])
def test_chest_tooltip_found_and_recognized(path):
    frame = cv2.imread(str(path))
    box = find_tooltip(frame, 200, 120)
    assert box is not None
    assert _is_chest(frame, box)
