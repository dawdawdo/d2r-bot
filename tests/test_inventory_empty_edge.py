"""An empty cell with a lit grid line along one edge is still empty (stowaway saw a ghost item, 2026-11-07)."""
import cv2

from bot.config import ROOT
from bot.vision.inventory import is_empty


def test_lit_edge_is_not_an_item():
    frame = cv2.imread(str(ROOT / "fixtures" / "inventory" / "empty_cell_lit_edge_3_0.png"))
    assert is_empty(frame, 3, 0)
    assert not is_empty(frame, 3, 1)  # the skull below
    assert not is_empty(frame, 2, 2)  # the key
