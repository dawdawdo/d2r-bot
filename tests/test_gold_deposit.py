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


def test_stash_gold_shown():
    from bot.town import stash_gold_shown
    assert stash_gold_shown(cv2.imread(str(FIX / "gold_after_keep.png")))       # shared 685976
    assert not stash_gold_shown(cv2.imread(str(FIX / "gold_carried_910k.png")))  # personal 19


def test_withdraw_and_deposit_boxes_differ():
    w = cv2.imread(str(TPL.parent / "withdraw_dialog.png"))
    d = cv2.imread(str(TPL))
    wroi = cv2.imread(str(FIX / "withdraw_dialog.png"))[250:330, 560:720]
    droi = cv2.imread(str(FIX / "deposit_dialog.png"))[250:330, 560:720]
    assert cv2.matchTemplate(wroi, w, cv2.TM_CCOEFF_NORMED).max() >= 0.8
    assert cv2.matchTemplate(wroi, d, cv2.TM_CCOEFF_NORMED).max() < 0.8
    assert cv2.matchTemplate(droi, w, cv2.TM_CCOEFF_NORMED).max() < 0.8
