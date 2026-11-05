"""Chronicle filter generator, on a synthetic Chronicle and the 3.0 game tables."""
import json
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import chronicle_filter as cf  # noqa: E402

FIX = ROOT / "fixtures" / "chronicle"
# Base codes from Chronicle_Filter_Handoff.md (Nov 4), as realistic input for the rules
SNAP_UNIQUE = set("""6hx 6l7 6lw 6rx 6ws 7b7 7bk 7bl 7br 7cr 7cs 7fl 7ga 7gd 7gi 7gl 7gm 7gw 7ha 7kr 7ls 7lw 7m7 7p7 7pa 7s7 7sb
7sc 7sr 7ta 7ts 7wa 7wc 7wh 7ws 8cb 8cs 8l8 8lb 8lw 8mx 8rx 8sw 8ws 92a 9ax 9b9 9ba 9bt 9dg 9gd 9gi 9gm 9gs 9gw 9m9 9ma 9mp 9mt
9p9 9qs 9sc 9sr 9tw 9vo 9wc 9wn 9ws 9yw am7 am9 amb amd amf amu bac bad bae bar bsd bsh buc ci2 ci3 clb cm1 cm2 cm3 cst dgr drb dre
fla flb ghm gsc hax hla jew lbw lea lgl lst mac nef obf pa9 pac pae pax qui rin sbw scp sml spc ssd sst uar uh9 uhb uhg uhm uit ulc
uld ulm umg uml upk urn utb utc uts utu uui uul uvb uvc uvg vip wac wae waf wnd wst xar xcl xhb xhl xhm xlm xmb xml xow xsk xtb xtg
xts ywn zhb zmb ztb zvb""".split())
SNAP_SET = set("6cs 7gd 7qr 7wd 7ws aar amu ba5 cap ci3 ful gsc lbl lbt lea lgl lrg ne9 paf qui sml uar uh9 uhm ult uth uul vbt "
               "xmg xml ztb".split())


def synthetic_stash(sets: list[int], uniques: list[int], runewords: list[int]) -> bytes:
    """A shared stash's last section in the Nov 4 layout. Built here so no real save lands in the repo."""
    records = [(1, 29500000, i) for i in [*sets, *uniques, *runewords]] + [(0, 29500000, 0)]
    head = cf.MAGIC + struct.pack("<4H", 1, len(sets) + 1, len(uniques), len(runewords))
    return b"\x55\xaa\x55\xaa junk" + head.ljust(24, b"\0") + b"".join(struct.pack("<HII", *r) for r in records)


@pytest.fixture(scope="module")
def data():
    uniques, sets = cf.load_tables(FIX)
    owned_sets = [int(r["*ID"]) for r in cf.eligible(sets)][:103]
    owned_uniques = [int(r["*ID"]) for r in cf.eligible(uniques)][:203]
    chron = cf.parse_chronicle(synthetic_stash(owned_sets, owned_uniques, [20000, 20001, 20002, 20003, 20004]))
    return chron, uniques, sets, *cf.missing(uniques, sets, chron)


def old_filter() -> dict:
    return json.loads((ROOT / "filters" / "LK Bot.fltr").read_text(encoding="utf-8-sig"))


def test_counts(data):
    chron, uniques, sets, _, _ = data
    assert (len(chron.sets), len(chron.uniques), len(chron.runewords)) == (103, 203, 5)
    assert (len(cf.eligible(uniques)), len(cf.eligible(sets))) == (403 - len(cf.QUEST), 135)


def test_missing_is_eligible_minus_owned(data):
    chron, uniques, sets, miss_u, miss_s = data
    assert (len(miss_u), len(miss_s)) == (398 - 203, 135 - 103)
    assert not {int(r["*ID"]) for r in miss_u} & chron.uniques
    assert not {int(r["*ID"]) for r in miss_s} & chron.sets


def test_quest_items_never_missing(data):
    *_, miss_u, _ = data
    assert not {r["index"] for r in miss_u} & cf.QUEST


def test_unknown_layout_refused():
    raw = bytearray(synthetic_stash(list(range(103)), list(range(203)), [20000, 20001, 20002, 20003, 20004]))
    at = raw.rfind(cf.MAGIC)
    struct.pack_into("<H", raw, at + 6, 50)  # wrong set count: the split no longer lands on the trailer
    with pytest.raises(ValueError):
        cf.parse_chronicle(bytes(raw))
    with pytest.raises(ValueError):
        cf.parse_chronicle(b"no chronicle here")


def test_filter_rules():
    new = cf.build_filter(old_filter(), SNAP_UNIQUE, SNAP_SET)
    rules = {r["name"]: r for r in new["rules"]}
    u, s = rules[cf.RULE_UNIQUES], rules[cf.RULE_SETS]
    assert u["equipmentRarity"] == ["unique"] and s["equipmentRarity"] == ["set"]
    assert set(u["equipmentItemCode"]) == SNAP_UNIQUE - {"rin", "amu", "jew", "cm1", "cm2", "cm3"}
    assert set(s["equipmentItemCode"]) == SNAP_SET - {"amu"}
    assert rules[cf.RULE_SET_CATEGORIES]["equipmentCategory"] == ["amule"]
    # no rule may pair a rarity with itemCode: the game reads that as "this rarity, or these items"
    for r in new["rules"]:
        assert not ("itemCode" in r and "equipmentRarity" in r), r["name"]
        assert "+" not in r["name"]  # the game drops such a rule
    for name in cf.GENERATED - {"Show Chronicle missing set jewelry"}:
        assert len(name) <= 32, name  # the game dropped both 34-char rules on rewrite and kept a 32-char one


def test_existing_pickups_kept():
    old = old_filter()
    new = cf.build_filter(old, SNAP_UNIQUE, SNAP_SET)
    rules = {r["name"]: r for r in new["rules"]}
    for name in ("Hide all gear", "Hide misc", "Hide gems", "Show unique rings", "Show Pul and higher runes",
                 "Show rejuvenation potions and keys", "Show charms", "Show flawless and perfect gems"):
        assert rules[name] == next(r for r in old["rules"] if r["name"] == name)
    assert set(rules["Show BiS uniques"]["equipmentItemCode"]) == {"uvg", "ulc", "usk"}
    assert rules[cf.RULE_AMULETS]["equipmentCategory"] == ["amule"]
    assert rules[cf.RULE_JEWELS]["itemCode"] == ["jew"]
    assert rules["Show Tal Rasha Lidless Eye"]["equipmentItemCode"] == ["oba"]
    assert [r["name"] for r in new["rules"]][:3] == ["Hide all gear", "Hide misc", "Hide gems"]  # later rules win


def test_every_gem_shown():
    new = cf.build_filter(old_filter(), SNAP_UNIQUE, SNAP_SET)
    shown = {c for r in new["rules"] if r["ruleType"] == "show" and r["enabled"] for c in r.get("itemCode", [])}
    hidden = next(r for r in new["rules"] if r["name"] == "Hide gems")["itemCode"]
    assert set(hidden) <= shown and len(hidden) == 35


def test_regenerating_replaces_rather_than_stacks():
    once = cf.build_filter(old_filter(), SNAP_UNIQUE, SNAP_SET)
    twice = cf.build_filter(once, {"hax"}, set())
    names = [r["name"] for r in twice["rules"]]
    assert len(names) == len(set(names))
    assert next(r for r in twice["rules"] if r["name"] == cf.RULE_UNIQUES)["equipmentItemCode"] == ["hax"]
    assert cf.RULE_SETS not in names


def test_empty_list_when_nothing_is_missing():
    names = [r["name"] for r in cf.build_filter(old_filter(), set(), set())["rules"]]
    assert cf.RULE_UNIQUES not in names and cf.RULE_SETS not in names
