from collections import Counter

from bot import cube


def final(counts, steps):
    have = Counter(counts)
    for inputs, out in steps:
        for k, v in inputs.items():
            have[k] -= v
            assert have[k] >= 0, (k, inputs)
        have[out] += 1
    return have


def test_keeps_five_and_cascades():
    steps = cube.plan({"El": 14})
    assert steps == [({"El": 3}, "Eld")] * 3
    assert final({"El": 14}, steps)["El"] == 5


def test_made_runes_feed_the_next_step():
    counts = {"El": 5 + 3 * 3, "Eld": 7}  # 3 new Eld -> 10 Eld -> one Tir
    have = final(counts, cube.plan(counts))
    assert (have["El"], have["Eld"], have["Tir"]) == (5, 7, 1)


def test_rune_recipes_use_their_gems_down_to_none():
    assert cube.plan({"Thul": 8}) == []
    assert cube.plan({"Thul": 11, "Chipped Topaz": 1}) == [({"Thul": 3, "Chipped Topaz": 1}, "Amn")]
    assert cube.plan({"Thul": 8, "Chipped Topaz": 5}, gem_keep=5) == []  # the old rule, still configurable


def test_runes_take_gems_before_gem_upgrades():
    counts = {"Thul": 11, "Chipped Topaz": 8}
    have = final(counts, cube.plan(counts))
    assert have["Amn"] == 2 and have["Chipped Topaz"] == 6 and have["Flawed Topaz"] == 0
    assert final({"Thul": 30, "Chipped Topaz": 3}, cube.plan({"Thul": 30, "Chipped Topaz": 3}))["Chipped Topaz"] == 0


def test_never_past_fal():
    counts = {"Fal": 20, "Flawed Ruby": 20, "Ko": 8, "Flawed Sapphire": 6}
    have = final(counts, cube.plan(counts))
    assert have["Lem"] == 0 and have["Fal"] == 21


def test_gems_for_runes_are_never_cubed_up():
    counts = {"Chipped Topaz": 30, "Flawed Sapphire": 30, "Chipped Skull": 30, "Flawed Emerald": 30}
    have = final(counts, cube.plan(counts))
    assert have["Chipped Topaz"] == 30 and have["Flawed Sapphire"] == 30
    assert have["Chipped Skull"] < 30 and have["Flawed Emerald"] < 30  # nothing needs these


def test_gems_climb_to_perfect_and_skulls_too():
    counts = {"Flawless Ruby": 99, "Skull": 8}
    have = final(counts, cube.plan(counts, top_grade="Perfect"))
    assert have["Flawless Ruby"] in (5, 6, 7) and have["Perfect Ruby"] == (99 - have["Flawless Ruby"]) // 3
    assert have["Flawless Skull"] == 1


def test_default_stops_at_flawless():
    counts = {"Flawless Ruby": 90, "Ruby": 8}
    have = final(counts, cube.plan(counts))
    assert have["Perfect Ruby"] == 0 and have["Flawless Ruby"] == 91

def test_full_stack_not_overfilled():
    from bot.cube import gem, plan

    steps = plan({gem("", "Sapphire"): 30, gem("Flawless", "Sapphire"): 99}, top_grade="Perfect")
    have = {gem("", "Sapphire"): 30, gem("Flawless", "Sapphire"): 99}
    for inputs, out in steps:
        for k, v in inputs.items():
            have[k] -= v
        have[out] = have.get(out, 0) + 1
        assert have[out] <= 99
    assert have[gem("Perfect", "Sapphire")] > 0  # the full stack drained into Perfects


def test_gem_short_names_runes_held_back_by_their_gem():
    counts = {"Amn": 30, "Chipped Amethyst": 2, "Thul": 4}
    steps = cube.plan(counts)
    assert len([s for s in steps if s[1] == "Sol"]) == 2
    assert cube.gem_short(counts, steps) == {"Amn": (24, "Chipped Amethyst", 0)}
