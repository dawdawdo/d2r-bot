"""The one switch between keeping her safe and more runs an hour."""
import yaml

from bot.config import DEFAULT_CONFIG, load_config


def with_risk(tmp_path, level):
    cfg = yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8-sig"))
    cfg["risk"] = level
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return load_config(path)


def test_the_repo_runs_safe():
    assert load_config()["risk"] == "safe"


def test_safe(tmp_path):
    cfg = with_risk(tmp_path, "safe")
    assert cfg["meph"]["clear_before_loot"] is True
    assert cfg["meph"]["safety"]["chicken_hp_pct"] == 40
    assert cfg["meph"]["safety"]["potion_hp_pct"] == 60  # the rest of the block stays
    assert not cfg["meph"].get("after_kill")
    assert cfg["town"]["refill_no_potions"] is False
    assert cfg["town"]["refill_rejuvs"] == 40


def test_fast(tmp_path):
    cfg = with_risk(tmp_path, "fast")
    assert cfg["meph"]["clear_before_loot"] is False
    assert cfg["meph"]["safety"]["chicken_hp_pct"] == 25
    assert cfg["meph"]["after_kill"] == {"potion_hp_pct": 40, "potion_mp_pct": 25}
    assert cfg["town"]["refill_no_potions"] is True
