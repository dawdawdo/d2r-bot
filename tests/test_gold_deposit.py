"""Deposit step pictures (live 2026-11-19, GLaDOS): carried gold box and the Deposit dialog."""
from pathlib import Path

import cv2

from bot.town import carried_gold_empty

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"
TPL = Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates" / "deposit_dialog.png"


def test_carried_gold_empty():
    assert not carried_gold_empty(cv2.imread(str(FIX / "gold_carried_910k.png")))
    assert carried_gold_empty(cv2.imread(str(FIX / "gold_carried_0.png")))


def test_deposit_dialog_template():
    t = cv2.imread(str(TPL))
    for name, want in (("deposit_dialog.png", True), ("gold_carried_0.png", False), ("gold_carried_910k.png", False)):
        roi = cv2.imread(str(FIX / name))[250:330, 560:720]
        assert (cv2.matchTemplate(roi, t, cv2.TM_CCOEFF_NORMED).max() >= 0.8) == want
