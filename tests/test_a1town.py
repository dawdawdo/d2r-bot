"""Act 1 town services (bot/a1town.py): automap labels, NPC menus. Frames from the 2026-11-23 Rogue Encampment probes."""
from pathlib import Path

import cv2
import pytest

from bot import a1town

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "a1town"


def frame(name: str):
    return cv2.imread(str(FIX / f"{name}.png"))


def test_automap_labels_at_the_stash_spawn():
    labs = a1town.map_labels(frame("labels_charsi_kashya_stash"))
    assert set(labs) == {"charsi", "kashya", "stash"}  # Akara's part of town isn't drawn from there
    assert abs(labs["kashya"][0] - 690) <= 2 and abs(labs["kashya"][1] - 367) <= 2
    assert abs(labs["charsi"][0] - 590) <= 2 and abs(labs["stash"][0] - 624) <= 2


def test_automap_akara_label_and_her_offset():
    labs = a1town.map_labels(frame("labels_akara"))
    assert "akara" in labs and "charsi" not in labs
    dx, dy = a1town.world_offset("akara", labs["akara"])
    assert 1000 < dx < 1250 and 350 < dy < 500  # right and down, off screen (she stood by her tent)


def test_no_labels_without_the_automap():
    assert a1town.map_labels(frame("menu_charsi")) == {}


@pytest.mark.parametrize("name, npc", [("menu_kashya", "kashya"), ("menu_akara", "akara"), ("menu_charsi", "charsi")])
def test_each_npc_menu_is_told_apart(name, npc):
    from bot.vision.screen import match_score

    f = frame(name)
    assert a1town.npc_menu(None, f) is not None
    for other in ("kashya", "akara", "charsi"):
        t = cv2.imread(str(a1town.TEMPLATES / f"npc_{other}.png"))
        score, _ = match_score(f, t, (0, 0, 1280, 500))
        assert (score >= 0.8) == (other == npc), (other, score)


def test_warrivs_menu_is_nobody_we_click_lines_in():
    """His line 1 is Go East (Act 2): only menus with a confirmed NPC name get line clicks."""
    from bot.vision.screen import match_score

    f = frame("menu_warriv")
    assert a1town.npc_menu(None, f) is not None
    for npc in ("kashya", "akara", "charsi"):
        score, _ = match_score(f, cv2.imread(str(a1town.TEMPLATES / f"npc_{npc}.png")), (0, 0, 1280, 500))
        assert score < 0.8


def test_kashya_menu_without_a_dead_merc_has_no_resurrect_line():
    f = frame("menu_kashya")
    widths = a1town._line_widths(f, a1town.npc_menu(None, f))
    assert 0 < max(widths) < a1town.RESURRECT_W  # HIRE, CANCEL
    assert widths[0] > 25 and widths[1] > widths[0]  # HIRE then the wider CANCEL


@pytest.mark.parametrize("name, kinds", [("belt_antidote_col1", ["antidote", "mp", "hp", "mp"]),
                                         ("belt_empty_col1", [None, "mp", "hp", "mp"]),
                                         ("belt_hp_mp", ["hp", "mp", "hp", "mp"])])
def test_belt_reads_antidotes(name, kinds):
    """The pale antidote jar has no saturated pixels: without its template it read as an empty column (and every
    run would have gone to Akara)."""
    from bot.config import load_config
    from bot.vision.orbs import belt_kinds

    assert belt_kinds(frame(name), load_config()["vision"]["belt"]) == kinds


@pytest.mark.parametrize("kinds, want", [([None, "mp", "hp", "mp"], 1),          # healing and mana stay
                                         ([None, "mp", None, "mp"], 1),          # one empty one is healing's
                                         (["antidote", "mp", None, "mp"], 0),    # the last empty one is healing's
                                         ([None, None, None, None], 2),
                                         (["antidote", "mp", "antidote", "hp"], 0),
                                         (["antidote", None, None, "hp"], 1)])   # one for mana, one for antidotes
def test_antidote_columns_never_take_the_last_healing_or_mana_column(kinds, want):
    """11:23 2026-11-23: the emptied healing column became the second antidote column: no healing potions left."""
    assert a1town._antidote_cols(kinds) == want


def test_kashya_found_under_cains_label():
    """Her label half covered by Deckard Cain's (0.70): she's still found (LABEL_MIN_OF)."""
    labs = a1town.map_labels(frame("labels_akara"))
    assert "kashya" in labs and abs(labs["kashya"][0] - 587) <= 3


@pytest.mark.parametrize("name", ["menu_kashya", "menu_akara", "menu_charsi", "menu_warriv"])
def test_any_npc_menu_counts_as_up(name):
    assert a1town.menu_up(None, frame(name))


def test_no_menu_without_one():
    assert not a1town.menu_up(None, frame("labels_akara"))


@pytest.mark.parametrize("name, want", [("orb_poisoned", True), ("orb_healthy", False)])
def test_poisoned_life_orb(name, want):
    """Every Andariel chicken on 2026-11-23 had a green (poisoned) orb: the fight cures it with an antidote."""
    from bot.config import load_config
    from bot.vision.orbs import poisoned

    assert poisoned(frame(name), load_config()["vision"]["orbs"]["hp"]) is want


@pytest.mark.parametrize("name, want", [("info_terrorized_93", True), ("info_not_terrorized", False)])
def test_terrorized_line_in_the_area_info(name, want):
    """2026-11-23 18:00-19:00 Catacombs 4 was terrorized (level 93) and the bot fought anyway: 3 chickens in 15 min."""
    from bot.lk import terror_info

    assert terror_info(frame(name)) is want


def test_inventory_antidotes_are_potions_to_drink():
    """Never stashed: the stowaway drinks what potion_kind names (4 antidotes reached shared page 1, 2026-11-23)."""
    from bot.vision.inventory import potion_kind

    f = frame("inv_antidotes")
    assert potion_kind(f, 1, 2) == "antidote" and potion_kind(f, 2, 2) == "antidote"
    assert potion_kind(f, 3, 2) is None  # a topaz
