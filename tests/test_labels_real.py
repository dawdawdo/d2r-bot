"""Label detector on real loot frames: gold piles on the ground must not read as unique labels."""
from pathlib import Path

import cv2
import pytest

from bot.config import load_config
from bot.vision.labels import find_labels

CFG = load_config()
RAW = Path(__file__).resolve().parent.parent / "fixtures" / "raw"
FALSE_UNIQUES = ["pick_unique_1025-234423.png", "pick_unique_1026-002023.png",
                 "pick_unique_1026-002024.png", "pick_unique_1026-002026.png",
                 "pick_unique_1026-055328.png", "pick_unique_1026-055330.png",
                 "pick_unique_1026-182942.png", "pick_unique_1026-183520.png"]


@pytest.mark.parametrize("name", FALSE_UNIQUES)
def test_gold_pile_is_not_unique(name):
    p = RAW / name
    if not p.exists():
        pytest.skip("fixtures/raw is local-only (gitignored)")
    kinds = {k: CFG["vision"]["labels"][k] for k in ("unique", "rune", "set", "white")}
    img = cv2.imread(str(p))
    box = cv2.inRange(img, (0, 250, 250), (5, 255, 255))  # the yellow evidence box drawn over the pick
    img = cv2.inpaint(img, box, 3, cv2.INPAINT_TELEA)
    labels = find_labels(img, kinds, ignore=CFG["vision"]["label_ignore"])
    assert not [l for l in labels if l.kind != "white"]
    assert len(labels) >= 10  # the real gold labels around it are still found


def test_chat_terror_zone_text_is_not_a_rune():
    from pathlib import Path

    import cv2

    from bot.config import load_config
    from bot.vision.labels import find_labels

    cfg = load_config()
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "merc" / "chat_terror_zone.png"))
    kinds = {k: cfg["vision"]["labels"][k] for k in ("rune", "unique")}
    assert find_labels(img, kinds, ignore=cfg["vision"]["label_ignore"]) == []
