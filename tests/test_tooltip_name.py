"""Stash tooltips (logs/loot crops: the frame's x 400..1280, hovered cell in the name) -> the name's color:
blue = magic = a charm (the only magic items the LK filter shows) -> Blizzaga's personal stash tab."""
from pathlib import Path

import cv2
import pytest

from bot.config import load_config
from bot.vision.tooltip import name_kind

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"


@pytest.mark.parametrize("name,kind", [
    ("tt_small_charm_922_480.png", "magic"),
    ("tt_hel_rune_960_367.png", "rune"),
])
def test_tooltip_name_color(name, kind):
    labels = load_config()["vision"]["labels"]
    colored = {k: v for k, v in labels.items() if k != "white"}
    crop = cv2.imread(str(FIX / name))
    frame = cv2.copyMakeBorder(crop, 0, 0, 400, 0, cv2.BORDER_CONSTANT)
    x, y = (int(v) for v in name[:-4].split("_")[-2:])
    assert name_kind(frame, x, y, colored) == kind


def test_rejuv_tooltip_is_not_a_charm():
    labels = load_config()["vision"]["labels"]
    colored = {k: v for k, v in labels.items() if k != "white"}
    frame = cv2.copyMakeBorder(cv2.imread(str(FIX / "tt_full_rejuv_884_405.png")), 0, 0, 400, 0, cv2.BORDER_CONSTANT)
    assert name_kind(frame, 884, 405, colored) != "magic"
