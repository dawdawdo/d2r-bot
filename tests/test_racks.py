import cv2

from bot import lk



def test_ne_targets_carry_the_weapon_rack():
    ts = lk.bonfire_targets({"name": "east", "world": [1629, 776], "order": ["ne", "nw", "nw_deep"]})
    ne = next(t for t in ts if t["name"] == "east_ne")
    assert ne["racks_world"] == [[1629 + 558, 776 - 512]]
    assert all("racks_world" not in t for t in ts if t["name"] != "east_ne")


def test_rack_tooltip_matches_weapon_rack_not_chest_or_gold():
    from pathlib import Path
    d = Path(__file__).resolve().parent.parent / "fixtures" / "racks"
    rack, gold, stash = (cv2.imread(str(d / n)) for n in ("weapon_rack.png", "gold.png", "stash.png"))
    for img, want in ((rack, True), (gold, False), (stash, False)):
        f = cv2.copyMakeBorder(img, 10, 10, 10, 10, cv2.BORDER_CONSTANT)
        assert lk._is_rack(f, (10, 10, img.shape[1], img.shape[0])) is want
        assert not lk._is_chest(f, (10, 10, img.shape[1], img.shape[0])) or not want
