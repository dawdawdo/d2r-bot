"""Game settings read from the save folder (read only) and the chat-input check (live frames 2026-10-31:
chat open after Enter vs plain town view)."""
import json
from pathlib import Path

import cv2

from bot.gamesettings import chat_open, loot_profile, players_setting, profiles, read_settings

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "chat"


def test_chat_input_seen_only_when_open():
    assert chat_open(cv2.imread(str(FIX / "open.png")))
    assert not chat_open(cv2.imread(str(FIX / "closed.png")))


def cfg_for(tmp_path):
    return {"paths": {"save_dir": str(tmp_path)}, "game": {"character": "Blizzaga"}}


def test_settings_and_filter_profile(tmp_path):
    (tmp_path / "Settings.json").write_text(json.dumps({"AutoMapMode": 2, "Offline Difficulty Scaling": 3}))
    (tmp_path / "lootfilter.json").write_text(json.dumps({"Version": 1, "Profiles": {"Blizzaga": "Looting"}}))
    for name in ("Looting", "LK Bot", "Starter - Sorc"):
        (tmp_path / f"{name}.fltr").write_text("{}")
    cfg = cfg_for(tmp_path)
    assert read_settings(cfg)["AutoMapMode"] == 2
    assert players_setting(cfg) == 3
    assert loot_profile(cfg) == "Looting"
    assert profiles(cfg) == ["LK Bot", "Looting", "Starter - Sorc"]  # the dropdown's order


def test_missing_files_are_not_fatal(tmp_path):
    cfg = cfg_for(tmp_path)
    assert read_settings(cfg) == {}
    assert players_setting(cfg) is None
    assert loot_profile(cfg) is None


def test_act1_spawn_view():
    """The Rogue Encampment spawn (fixed map) vs Act 3/4 frames: only Act 1 frames match."""
    from bot.vision.screen import ASSETS

    t = cv2.imread(str(ASSETS / "a1_spawn.png"))

    def score(name):
        f = cv2.imread(str(FIX / name))
        return float(cv2.matchTemplate(f[0:300, 120:680], t, cv2.TM_CCOEFF_NORMED).max())

    assert score("a1_spawn.png") > 0.9 and score("closed.png") > 0.75
    other = cv2.imread(str(FIX.parent / "durance" / "hop_up_before.png"))
    assert float(cv2.matchTemplate(other[0:300, 120:680], t, cv2.TM_CCOEFF_NORMED).max()) < 0.6
