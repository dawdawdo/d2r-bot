"""Target uniques show whether or not the Chronicle has them (Stephen 2026-11-25: SoJ, Andariel's Visage, ...)."""
from bot import chronicle as cf

BASE = {"rules": [{"name": "Hide all gear", "enabled": True, "ruleType": "hide", "equipmentRarity": ["unique"]},
                  {"name": "Show BiS uniques", "enabled": True, "ruleType": "show", "equipmentRarity": ["unique"],
                   "equipmentItemCode": ["uvg", "usk", "ulc"]}]}


def _rule(flt, name):
    return next((r for r in flt["rules"] if r["name"] == name), None)


def test_targets_show_with_an_empty_missing_list():
    flt = cf.build_filter(BASE, set(), set())  # the Chronicle has everything
    t = _rule(flt, cf.RULE_TARGETS)
    assert t["equipmentRarity"] == ["unique"] and set(t["equipmentItemCode"]) == set(cf.TARGET_UNIQUES)
    rings = _rule(flt, cf.RULE_TARGET_RINGS)
    assert rings["equipmentRarity"] == ["unique"] and rings["equipmentCategory"] == ["rings"]
    assert {"usk", "uap", "umc", "zhb"} <= set(t["equipmentItemCode"])
    assert _rule(flt, "Show BiS uniques") is not None  # Stephen's own rules stay


def test_targets_come_before_nothing_and_regenerate_cleanly():
    once = cf.build_filter(BASE, {"7gd"}, set())
    twice = cf.build_filter(once, {"7gd"}, set())
    assert [r["name"] for r in once["rules"]] == [r["name"] for r in twice["rules"]]  # no duplicates on re-run
    assert cf.up_to_date(once, {"7gd"}, set())
    assert not cf.up_to_date(BASE, {"7gd"}, set())  # an old filter without the target rules needs regenerating


def test_rule_names_fit_the_game():
    assert len(cf.RULE_TARGETS) <= 32 and len(cf.RULE_TARGET_RINGS) <= 32
