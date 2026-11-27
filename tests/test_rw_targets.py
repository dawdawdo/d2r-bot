from collections import Counter

import pytest

from bot import chronicle as cf
from bot import rw_targets as rt


@pytest.fixture(scope="module")
def t():
    return rt.load()


def ids_for(t, names):
    """Chronicle ids for runeword names (inverse of rt.chronicle_name)."""
    out = set()
    for i in list(range(20500, 20700)) + list(range(27190, 27240)):
        if rt.chronicle_name(i, t) in names:
            out.add(i)
    return out


def test_chronicle_ids_name_known_runewords(t):
    assert rt.chronicle_name(20519, t) == "Call to Arms"
    assert rt.chronicle_name(20635, t) == "Spirit"


def test_fits_by_type_and_sockets(t):
    grief = next(r for r in t.runewords if r["name"] == "Grief")
    lore = next(r for r in t.runewords if r["name"] == "Lore")
    assert t.fits("7cr", grief) and not t.fits("utp", grief)  # Phase Blade is a sword; Archon Plate isn't
    assert t.fits("ci3", lore)  # circlets count as helms
    assert t.fits("7cr", grief, sockets=5) and not t.fits("7cr", grief, sockets=4)


def test_first_open_step_shown_until_the_stash_has_enough(t):
    steps = rt.targets(set(), t, Counter(), active=1, filter_codes=set(cf.RUNEWORD_BASES))
    assert steps[0]["code"] == "hbw" and steps[0]["shown"] and not any(s["shown"] for s in steps[1:])
    blade = next(s for s in steps if s["code"] == "7cr")  # last since 2026-11-27 (Stephen has his Grief base)
    assert "Grief" in blade["runewords"] and "Strength" not in blade["runewords"]  # a Flail carries Strength
    full = rt.targets(set(), t, Counter({"hbw": rt.CAP}), active=1, filter_codes=set(cf.RUNEWORD_BASES))
    assert not full[0]["shown"]


def test_step_closes_when_the_chronicle_has_its_runewords(t):
    done = ids_for(t, {"Death", "Grief", "King's Grace", "Kingslayer", "Lawbringer", "Unbending Will"})
    steps = rt.targets(done, t, Counter(), active=1, filter_codes=set(cf.RUNEWORD_BASES))
    assert steps[0]["code"] == "hbw" and steps[0]["shown"]


def test_big_rune_runewords_keep_no_step_open(t):
    steps = rt.targets(set(), t, Counter(), active=8, filter_codes=set(cf.RUNEWORD_BASES))
    names = {n for s in steps for n in s["runewords"]}
    assert not names & {"Last Wish", "Breath of the Dying", "Brand", "Faith", "Ice", "Mist", "Plague"}


def test_filter_rule_for_target_bases():
    old = {"rules": []}
    new = cf.build_filter(old, set(), set(), {"7cr", "fla"})  # Flail is already a runeword base: not repeated
    rules = {r["name"]: r for r in new["rules"]}
    assert rules[cf.RULE_RW_TARGETS]["equipmentItemCode"] == ["7cr"]
    assert rules[cf.RULE_RW_TARGETS]["equipmentRarity"] == ["normal"]
    assert rules[cf.RULE_SOCKETED_RW_TARGETS]["filterEtherealSocketed"] is True
    assert cf.up_to_date(new, set(), set(), {"7cr"})
    assert not cf.up_to_date(new, set(), set(), {"hbw"})
    again = cf.build_filter(new, set(), set(), set())
    assert cf.RULE_RW_TARGETS not in {r["name"] for r in again["rules"]}  # regenerated, not stacked
