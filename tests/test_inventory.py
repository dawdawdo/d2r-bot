from pathlib import Path

import cv2

from bot.config import load_config
from bot.vision.inventory import protected_cells, scan

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"
KEY = cv2.imread(str(Path(__file__).resolve().parent.parent / "bot" / "assets" / "templates" / "inv_key.png"))
PROT = protected_cells(load_config()["inventory"]["protected"])


def test_eight_key_stacks_and_a_rune():
    inv = scan(cv2.imread(str(FIX / "keys8_hel.png")), KEY, PROT)
    assert sorted(inv["key"]) == [(0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1)]
    assert inv["other"] == [(1, 3)]  # Hel rune
    assert inv["empty"] == [(0, 0)]


def test_helm_rune_key_and_empties():
    inv = scan(cv2.imread(str(FIX / "stash_shared_helm.png")), KEY, PROT)
    assert inv["key"] == [(2, 1)]
    assert sorted(inv["other"]) == [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]
    assert sorted(inv["empty"]) == [(0, 2), (0, 3), (1, 2), (1, 3)]


def test_protected_cells():
    assert len(PROT) == 30 and (2, 2) in PROT and (2, 1) not in PROT
