"""Per-character config profiles (bot/config.py apply_profile) and per-character state (bot/state.py use)."""
import pytest

from bot import state
from bot.config import ROOT, apply_profile, for_character, load_config, task_character


@pytest.fixture
def cfg(monkeypatch):
    monkeypatch.delenv("D2R_CHARACTER", raising=False)
    return load_config()


def test_default_character_is_blizzaga(cfg):
    assert cfg["game"]["character"] == "Blizzaga"
    assert cfg["game"]["default_character"] == "Blizzaga"


def test_smoked_profile_replaces_skills_and_protected(cfg):
    blizzard_route = cfg["game"]["route"]
    apply_profile(cfg, "Smoked")
    assert cfg["game"]["character"] == "Smoked"
    assert cfg["game"]["route"] != blizzard_route
    sk = cfg["hotkeys"]["skills"]
    assert sk["teleport"] == "s" and sk["concentration"] == "a"
    assert "blizzard" not in sk and "frozen_armor" not in sk  # replaced whole, not merged
    assert cfg["hotkeys"]["buffs"] == ["holy_shield"]
    assert cfg["hotkeys"]["warcries"] == []
    assert cfg["inventory"]["protected"] == []
    assert cfg["hotkeys"]["potions"] == ["1", "2", "3", "4"]  # untouched keys stay


def test_task_character(cfg):
    assert task_character(cfg, ["andy"]) == "Blizzaga"
    assert task_character(cfg, ["lk", "andy"]) == "Blizzaga"
    assert task_character(cfg, ["baal"]) == "Smoked"
    with pytest.raises(ValueError):
        task_character(cfg, ["andy", "baal"])


def test_for_character_copies(cfg):
    sm = for_character(cfg, "Smoked")
    assert sm["game"]["character"] == "Smoked"
    assert cfg["game"]["character"] == "Blizzaga"
    assert "blizzard" in cfg["hotkeys"]["skills"]
    assert for_character(cfg, "Blizzaga") is cfg


def test_unknown_profile(cfg):
    with pytest.raises(ValueError):
        apply_profile(cfg, "Nobody")


def test_env_character(monkeypatch):
    monkeypatch.setenv("D2R_CHARACTER", "Smoked")
    c = load_config()
    assert c["game"]["character"] == "Smoked" and c["game"]["default_character"] == "Blizzaga"


def test_state_per_character(monkeypatch):
    monkeypatch.setattr(state, "PATH", state.PATH)
    state.use("Smoked", "Blizzaga")
    assert state.PATH == ROOT / "logs" / "state_Smoked.json"
    state.use("Blizzaga", "Blizzaga")
    assert state.PATH == ROOT / "logs" / "state.json"


def test_baal_ready_uses_smoked_maps(cfg, monkeypatch):
    from bot.tasks import baal as tb

    seen = []
    monkeypatch.setattr(tb, "level_exit", lambda c, f: seen.append(c["game"]["route"]) or True)
    tb.Baal.ready(cfg)
    assert seen and all(r == "smoked_hell" for r in seen)
    assert cfg["game"]["route"] != "smoked_hell"
