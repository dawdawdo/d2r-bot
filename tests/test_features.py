"""config.yaml `features:`: one switch per run extra (Stephen 2026-11-20)."""
import pytest

from bot.config import FEATURES, apply_features, load_config


def test_every_feature_is_in_config_yaml():
    feats = load_config()["features"]
    assert set(feats) == set(FEATURES) | {"charms"}


def test_features_set_the_keys_the_code_reads():
    cfg = {"features": {"gold_pickup": True, "weapon_racks": False, "cube": False, "skip_huts": ["west_nw_deep"],
                        "charms": False},
           "loot": {"pick": ["rune", "magic", "gray"]}, "cube": {"enabled": True}}
    apply_features(cfg)
    assert cfg["loot"]["pick_gold"] is True and cfg["lk"]["racks"] is False and cfg["cube"]["enabled"] is False
    assert cfg["lk"]["skip_targets"] == ["west_nw_deep"] and cfg["loot"]["pick"] == ["rune", "gray"]
    cfg["features"]["charms"] = True
    apply_features(cfg)
    assert cfg["loot"]["pick"].count("magic") == 1


def test_a_typo_is_an_error_not_a_silent_no_op():
    with pytest.raises(ValueError, match="gold_pickpu"):
        apply_features({"features": {"gold_pickpu": True}})


def test_skip_huts_names_real_targets():
    from bot.lk import load_route

    cfg = load_config()
    route = load_route(cfg["game"]["route"])
    names = {t["name"] for t in route["targets"]}
    assert set(cfg["features"]["skip_huts"]) <= names
    assert {"east_ne", "west_nw_deep"} <= names
