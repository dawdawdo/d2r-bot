"""Template fallback for chests the hover scan misses (bot/lk.py find_chest_template)."""
import json
from pathlib import Path

import cv2
import pytest

from bot.lk import chest_templates, find_chest_template

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "fixtures" / "det" / "labels.jsonl"


def _hand_labels():
    if not LABELS.exists():
        return []
    rows = [json.loads(l) for l in LABELS.read_text().splitlines() if l.strip()]
    return [r for r in rows if r["why"] != "proposal" and (ROOT / r["frame"]).exists()]


def test_templates_ship():
    assert len(chest_templates()) == 16 and all(t is not None for t in chest_templates())


@pytest.mark.skipif(not _hand_labels(), reason="failure frames are not in git")
def test_finds_labeled_chests_and_nothing_where_none():
    for r in _hand_labels():
        f = cv2.imread(str(ROOT / r["frame"]))
        chests = [b for b in r["boxes"] if b[0] == "chest"]
        if chests:
            _, x, y, w, h = chests[0]
            hit = find_chest_template(f, x + w // 2 - 19, y + h // 2 - 29)  # the typical miss offset
            assert hit is not None, r["frame"]
            assert abs(hit[0] - (x + w // 2)) < 12 and abs(hit[1] - (y + h // 2)) < 12, r["frame"]
        elif r["why"] == "no_chest_in_view":
            assert find_chest_template(f, 640, 330, win=400) is None, r["frame"]
