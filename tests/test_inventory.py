from pathlib import Path

import cv2

from bot.config import load_config
from bot.vision.inventory import protected_cells, scan

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"
KEY = cv2.imread(str(Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates" / "inv_key.png"))
PROT = protected_cells(load_config()["inventory"]["protected"])
OLD_PROT = protected_cells([[3, 0, 7, 4], [2, 2, 1, 2]])  # Stephen's layout when the older fixtures were taken


def test_eight_key_stacks_and_a_rune():
    inv = scan(cv2.imread(str(FIX / "keys8_hel.png")), KEY, OLD_PROT)
    assert sorted(inv["key"]) == [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1)]
    assert inv["other"] == [(1, 3)]  # Hel rune
    assert inv["empty"] == [(0, 0)]


def test_helm_rune_key_and_empties():
    inv = scan(cv2.imread(str(FIX / "stash_shared_helm.png")), KEY, OLD_PROT)
    assert inv["key"] == [(2, 1)]
    assert sorted(inv["other"]) == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]
    assert sorted(inv["empty"]) == [(0, 2), (0, 3), (1, 2), (1, 3)]


def test_protected_cells():
    assert len(PROT) == 27 and (3, 1) in PROT and (3, 0) not in PROT and (9, 3) in PROT


def test_current_layout_touches_none_of_stephens_items():
    """2026-11-03 after the respec: every charm, tome, the skull and the cube are protected; the key is the key."""
    inv = scan(cv2.imread(str(FIX / "respec_20261103.png")), KEY, PROT)
    assert inv["key"] == [(3, 0)]
    assert inv["other"] == []
    assert sorted(inv["empty"]) == [(c, r) for c in range(3) for r in range(4)]


def test_weapon_set_tabs():
    from bot.vision.inventory import weapon_set

    assert weapon_set(cv2.imread(str(FIX / "respec_20261103.png"))) == 2
    assert weapon_set(cv2.imread(str(FIX / "weapons_cta_20261103.png"))) == 1


def test_runes_added_hel():
    from bot.vision.inventory import runes_added

    a = cv2.imread(str(FIX / "runes_tab_before.png"))
    b = cv2.imread(str(FIX / "runes_tab_hel_added.png"))
    assert runes_added(a, b) == ["Hel"]
    assert runes_added(a, a) == []
