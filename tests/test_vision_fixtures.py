"""Detectors against real labeled frames in fixtures/labeled/<state>/*.png (+ .json)."""
import json
from pathlib import Path

import cv2
import pytest

from bot.config import ROOT, load_config
from bot.vision.labels import find_labels
from bot.vision.orbs import orb_pcts
from bot.vision.screen import ScreenClassifier

CFG = load_config()["vision"]
CASES = sorted((ROOT / "fixtures" / "labeled").glob("*/*.png"))
ORB_TOL = 8  # percentage points


def _meta(png: Path) -> dict:
    j = png.with_suffix(".json")
    return json.loads(j.read_text()) if j.exists() else {"state": png.parent.name}


@pytest.fixture(scope="module")
def classifier():
    return ScreenClassifier.from_config(CFG["states"])


if not CASES:
    pytest.skip("no labeled fixtures yet (M1)", allow_module_level=True)


@pytest.mark.parametrize("png", CASES, ids=lambda p: f"{p.parent.name}/{p.stem}")
def test_fixture(png, classifier):
    meta = _meta(png)
    frame = cv2.imread(str(png))
    assert frame.shape[:2] == (720, 1280)
    assert classifier.classify(frame) == meta["state"]
    if "hp" in meta or "mp" in meta:
        pcts = orb_pcts(frame, CFG["orbs"])
        for k in ("hp", "mp"):
            if k in meta:
                assert abs(pcts[k] - meta[k]) <= ORB_TOL, (k, pcts[k], meta[k])
    if "labels" in meta:
        kinds = {k: v for k, v in CFG["labels"].items() if k != "white"}  # white = testing-only kind
        found = sorted({l.kind for l in find_labels(frame, kinds, ignore=CFG["label_ignore"])})
        assert found == meta["labels"]
