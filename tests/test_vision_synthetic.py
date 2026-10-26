"""Detector logic on synthetic frames. Real-frame tests live in test_vision_fixtures.py."""
import cv2
import numpy as np
import pytest

from bot.config import load_config
from bot.vision.labels import find_labels
from bot.vision.orbs import orb_fill, orb_pcts
from bot.vision.screen import Cue, ScreenClassifier, is_loading, match_score

CFG = load_config()["vision"]
CFG["labels"] = {k: v for k, v in CFG["labels"].items() if k != "white"}  # white = testing-only kind


def blank(h=720, w=1280, val=20):
    return np.full((h, w, 3), val, np.uint8)


@pytest.mark.parametrize("pct", [0, 10, 35, 50, 70, 100])
def test_orb_fill_levels(pct):
    f = blank()
    x, y, w, h = CFG["orbs"]["hp"]["region"]
    fill = round(h * pct / 100)
    if fill:
        f[y + h - fill : y + h, x : x + w] = (20, 20, 200)  # BGR red
    assert orb_fill(f, (x, y, w, h), CFG["orbs"]["hp"]["color"]) == pytest.approx(pct / 100, abs=0.02)


def test_orb_pcts_hp_and_mp_independent():
    f = blank()
    x, y, w, h = CFG["orbs"]["hp"]["region"]
    f[y + h // 2 : y + h, x : x + w] = (20, 20, 200)
    x, y, w, h = CFG["orbs"]["mp"]["region"]
    f[y : y + h, x : x + w] = (200, 60, 20)  # BGR blue
    p = orb_pcts(f, CFG["orbs"])
    assert p["hp"] == pytest.approx(50, abs=2)
    assert p["mp"] == pytest.approx(100, abs=2)


def bgr_from_rgb(r, g, b):
    return (b, g, r)


def draw_label(f, text, org, rgb):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    x, y = org
    cv2.rectangle(f, (x - 4, y - th - 4), (x + tw + 4, y + 7), (10, 10, 10), -1)  # room for descenders
    cv2.putText(f, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, bgr_from_rgb(*rgb), 1, cv2.LINE_AA)


def test_label_colors_classified():
    f = blank(val=40)
    draw_label(f, "Harlequin Crest", (200, 200), (199, 179, 119))  # unique gold
    draw_label(f, "Ber Rune", (600, 300), (255, 168, 0))           # rune orange
    draw_label(f, "Tal Rasha's Lidless Eye", (300, 450), (0, 252, 0))  # set green
    draw_label(f, "Crystal Sword", (800, 500), (255, 255, 255))    # white: ignored
    labels = find_labels(f, CFG["labels"])
    kinds = sorted(l.kind for l in labels)
    assert kinds == ["rune", "set", "unique"], labels
    rune = next(l for l in labels if l.kind == "rune")
    assert 600 <= rune.center[0] <= 680 and 285 <= rune.center[1] <= 305


def test_label_ignore_region():
    f = blank(val=40)
    draw_label(f, "Ber Rune", (600, 650), (255, 168, 0))
    assert find_labels(f, CFG["labels"], ignore=[[0, 560, 1280, 160]]) == []


def test_loading_detection():
    assert is_loading(np.zeros((720, 1280, 3), np.uint8))
    f = np.zeros((720, 1280, 3), np.uint8)
    cv2.putText(f, "Loading", (500, 360), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    assert is_loading(f)  # a little text is still loading
    assert not is_loading(blank(val=90))


def test_screen_classifier_order_and_fallbacks():
    rng = np.random.default_rng(0)
    f = rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8)
    tmpl_a = f[100:140, 100:200].copy()
    tmpl_b = rng.integers(0, 255, (40, 100, 3), dtype=np.uint8)
    clf = ScreenClassifier({
        "b_state": [Cue(tmpl_b, (0, 0, 400, 300), 0.9)],
        "a_state": [Cue(tmpl_a, (50, 50, 300, 200), 0.9)],
    })
    assert clf.classify(f) == "a_state"
    score, loc = match_score(f, tmpl_a, (50, 50, 300, 200))
    assert score > 0.99 and loc == (100, 100)
    assert clf.classify(np.zeros_like(f)) == "loading"
    assert clf.classify(rng.integers(0, 255, f.shape, dtype=np.uint8)) == "unknown"


def test_classifier_from_empty_config():
    assert ScreenClassifier.from_config({}).classify(blank()) == "unknown"
