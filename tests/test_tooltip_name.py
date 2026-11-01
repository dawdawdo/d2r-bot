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


def test_rejuv_tooltip_found_by_word():
    """Spare rejuvs are told apart in the stash loop (their Materials stack caps at 99)."""
    from types import SimpleNamespace

    from bot.town import _is_rejuv

    bot = SimpleNamespace(_templates={})
    pad = lambda n: cv2.copyMakeBorder(cv2.imread(str(FIX / n)), 0, 0, 400, 0, cv2.BORDER_CONSTANT)  # noqa: E731
    assert _is_rejuv(bot, pad("tt_full_rejuv_884_405.png"), 884, 405)
    assert not _is_rejuv(bot, pad("tt_small_charm_922_480.png"), 922, 480)
    assert not _is_rejuv(bot, pad("tt_hel_rune_960_367.png"), 960, 367)


def test_charm_word_in_tooltips_and_labels():
    """Blue isn't enough (a magic Amulet showed, "Eligible for Chronicle"): the word "Charm" decides."""
    from bot.town import _is_charm
    from bot.vision.labels import Label, is_charm

    pad = lambda n: cv2.copyMakeBorder(cv2.imread(str(FIX / n)), 0, 0, 400, 0, cv2.BORDER_CONSTANT)  # noqa: E731
    assert _is_charm(pad("tt_small_charm_922_480.png"), 922, 480)
    assert not _is_charm(pad("tt_hel_rune_960_367.png"), 960, 367)
    assert not _is_charm(pad("tt_full_rejuv_884_405.png"), 884, 405)
    # ground label: same font as the tooltip name ("Small Charm" box from the tooltip; the Amulet as picked)
    assert is_charm(pad("tt_small_charm_922_480.png"), Label("magic", 858, 368, 133, 14))
    amulet = cv2.imread(str(FIX.parent / "loot" / "magic_amulet_label_423_260_79_13.png"))
    assert not is_charm(amulet, Label("magic", 423, 260, 79, 13))
