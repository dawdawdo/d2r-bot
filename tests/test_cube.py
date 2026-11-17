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
    have = final(counts, cube.plan(counts, top="Fal"))
    assert have["Lem"] == 0 and have["Fal"] == 21


def test_gems_for_runes_keep_a_reserve_only():
    counts = {"Chipped Topaz": 30, "Flawed Sapphire": 30, "Chipped Skull": 30, "Emerald": 30}
    have = final(counts, cube.plan(counts))
    assert have["Chipped Topaz"] == 30 and have["Flawed Sapphire"] == 30
    assert have["Chipped Skull"] < 30 and have["Emerald"] < 30  # nothing needs these


def test_full_rune_gem_stack_gets_cubed_down_to_the_reserve():
    counts = {"Flawed Sapphire": 99, "Flawed Topaz": 85}  # 2026-11-15 stash
    have = final(counts, cube.plan(counts, reserve=30))
    assert 30 <= have["Flawed Sapphire"] <= 32 and have["Sapphire"] + have["Flawless Sapphire"] > 0
    assert 30 <= have["Flawed Topaz"] <= 32


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


def test_ist_and_up_are_never_cubed():
    counts = {r: 50 for r in cube.RUNES}
    steps = cube.plan(counts, top="Zod")
    used = {k for inputs, _ in steps for k in inputs}
    assert not used & set(cube.RUNES[cube.RUNES.index("Ist"):])


def test_cubes_up_through_ist_with_two_rune_recipes_from_pul():
    counts = {"Fal": 20, "Lem": 10, "Pul": 14, "Um": 3, "Mal": 11, "Ist": 1, "Gul": 15,
              "Flawed Ruby": 40, "Flawed Emerald": 40, "Flawed Diamond": 40, "Topaz": 40, "Amethyst": 40}
    steps = cube.plan(counts, top="Ist")
    for inputs, out in steps:
        rune = next((k for k in inputs if k in cube.RUNES), None)
        if rune is None:
            continue  # a gem upgrade
        assert inputs[rune] == (2 if rune in ("Pul", "Um", "Mal") else 3)
        assert inputs[cube.RUNE_GEM[rune]] == 1
    have = final(counts, steps)
    assert have["Ist"] > 1 and have["Gul"] == 15 and have["Mal"] in (5, 6)
    assert all(have[r] >= 5 for r in ("Fal", "Lem", "Pul", "Um", "Mal"))
