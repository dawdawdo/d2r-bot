"""Merc portrait (alive/dead) and Asheara's dialog against real frames in fixtures/merc/."""
from pathlib import Path

import cv2
import pytest

from bot.vision.screen import ASSETS, match_score

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "fixtures" / "merc"


def _score(frame: str, template: str, region=None) -> tuple[float, tuple[int, int]]:
    img = cv2.imread(str(FIX / frame))
    if img is None:
        pytest.skip(f"missing fixture {frame}")
    return match_score(img, cv2.imread(str(ASSETS / template)), region)


def test_merc_alive():
    assert _score("alive.png", "merc_portrait.png", (0, 0, 78, 74))[0] >= 0.85


def test_merc_dead():
    assert _score("dead.png", "merc_portrait.png", (0, 0, 78, 74))[0] < 0.85


def test_asheara_dialog():
    score, loc = _score("asheara_dialog.png", "npc_asheara.png", (0, 0, 1280, 500))
    assert score >= 0.85 and loc == (543, 115)


@pytest.mark.parametrize("frame,expected", [("lk_wp_merc_left.png", True), ("lk_wp_merc_glow.png", True),
                                            ("alive.png", False)])
def test_fingerprint_with_merc(frame, expected):
    import yaml

    from bot.lk import fingerprint_match

    fp = yaml.safe_load((ROOT / "maps" / "blizzaga_hell" / "route.yaml").read_text())["fingerprint"]
    img = cv2.imread(str(FIX / frame))
    tpl = cv2.imread(str(ASSETS / fp["template"]))
    assert fingerprint_match(img, tpl, fp["region"], fp["threshold"], fp.get("half_threshold")) is expected


def test_asheara_not_in_town_frame():
    assert _score("alive.png", "npc_asheara.png", (0, 0, 1280, 500))[0] < 0.85


def test_arrival_view_change():
    from bot.town import arrived

    town = cv2.imread(str(FIX / "alive.png"))
    lk = cv2.imread(str(FIX / "lk_wp_merc_left.png"))
    assert arrived(town, lk)
    assert not arrived(town, town)


def test_fingerprint_closes_an_inventory_panel_left_up(monkeypatch):
    """2026-11-26 03:00: the inventory was still up after the war cries; the check called it a changed map."""
    import numpy as np

    from bot import lk, town
    from bot.vision import inventory

    panel = {"up": True}
    closed = []

    class Bot:
        frame = None
        kill = type("K", (), {"sleep": staticmethod(lambda s: None)})()

        def observe(self):
            self.frame = np.full((720, 1280, 3), 1 if panel["up"] else 2, np.uint8)

        def save_failure(self, note):
            raise AssertionError("no failure expected")

    monkeypatch.setattr(lk, "_fp_template", lambda route: None)
    monkeypatch.setattr(inventory, "inventory_open", lambda f: int(f[0, 0, 0]) == 1)
    monkeypatch.setattr(town, "inventory_panel", lambda bot, want: closed.append(want) or panel.update(up=False))
    monkeypatch.setattr(lk, "fingerprint_match", lambda f, *a, **k: int(f[0, 0, 0]) == 2)
    lk.check_fingerprint(Bot(), {"fingerprint": {"region": None, "threshold": 0.8}})
    assert closed == [False]
