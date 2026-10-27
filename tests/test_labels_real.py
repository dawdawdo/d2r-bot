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


@pytest.mark.parametrize("name,word,count", [("rejuv_and_gold.png", "rejuv", 1), ("key_and_gold.png", "key", 1)])
def test_white_words(name, word, count):
    """Keys and rejuvs are told apart from the gold labels around them by their first word."""
    from bot.vision.labels import white_word

    img = cv2.imread(str(RAW.parent / "loot" / name))
    labels = find_labels(img, {"white": CFG["vision"]["labels"]["white"]}, ignore=CFG["vision"]["label_ignore"])
    words = [white_word(img, l) for l in labels]
    assert words.count(word) == count
    assert len([w for w in words if w is None]) >= 8  # gold


def test_loot_picks_key_not_gold():
    """loot() clicks the key (keys below a full stack) and none of the gold labels around it."""
    from types import SimpleNamespace

    from bot.lk import loot

    frame = cv2.imread(str(RAW.parent / "loot" / "key_and_gold.png"))
    clicks = []

    def click(x, y, *a, **k):  # picking the item removes its label
        clicks.append((x, y))
        cv2.rectangle(bot.frame, (x - 25, y - 10), (x + 25, y + 10), (60, 60, 60), -1)

    bot = SimpleNamespace(cfg=CFG, frame=frame.copy(), keys_left=2, _labels_known=True, check=lambda: None,
                          click=click, wait_still=lambda **k: True)
    assert loot(bot) == ["key"]
    assert clicks == [(717 + 37 // 2, 474 + 13 // 2)]
    assert bot.keys_left == 3
    bot.frame, bot.keys_left, clicks[:] = frame.copy(), 12, []
    assert loot(bot) == []  # full stack: leave it


def test_gap_between_gold_labels_is_not_unique():
    """2026-10-27: coins showing through between "495 Gold" and "1818 Gold" read as a unique."""
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "loot" / "false_unique_between_gold.png"))
    kinds = {k: CFG["vision"]["labels"][k] for k in ("unique", "rune", "set")}
    assert not find_labels(img, kinds, ignore=CFG["vision"]["label_ignore"])


def test_coin_blob_between_gold_labels_is_not_unique():
    """2026-10-27 04:20: a 19 px tall coin blob next to "426 Gold" / "1762 Gold" read as a unique."""
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "loot" / "false_unique_coins_19px.png"))
    kinds = {k: CFG["vision"]["labels"][k] for k in ("unique", "rune", "set")}
    assert not find_labels(img, kinds, ignore=CFG["vision"]["label_ignore"])


@pytest.mark.parametrize("name", sorted(p.name for p in (Path(__file__).resolve().parent.parent / "fixtures" / "loot").glob("pick_rune_*.png")))
def test_real_rune_labels_found(name):
    """Live rune picks (file name = label box x_y_w_h): the detector must still find them."""
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "loot" / name))
    x, y, w, h = map(int, name[:-4].split("_")[3:7])
    labels = find_labels(img, {"rune": CFG["vision"]["labels"]["rune"]}, ignore=CFG["vision"]["label_ignore"])
    assert any(abs(l.x - x) < 5 and abs(l.y - y) < 5 for l in labels)


def test_monster_between_gold_labels_is_not_unique():
    """2026-10-27 06:29: tan pixels (monster, coins) at the end of "1827 Gold" read as a unique."""
    img = cv2.imread(str(Path(__file__).resolve().parent.parent / "fixtures" / "loot" / "false_unique_monster_head.png"))
    kinds = {k: CFG["vision"]["labels"][k] for k in ("unique", "rune", "set")}
    assert not find_labels(img, kinds, ignore=CFG["vision"]["label_ignore"])
