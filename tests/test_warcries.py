"""War cries: the swap key is a toggle, so the bot must read the set instead of counting presses."""
from pathlib import Path

import cv2
import pytest

from bot.config import load_config
from bot.controller import Chicken
from bot.town import cast_warcries, ensure_main_weapons

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "inventory"
MAIN_FRAME = cv2.imread(str(FIX / "respec_20261103.png"))
CTA_FRAME = cv2.imread(str(FIX / "weapons_cta_20261103.png"))
HK = load_config()["hotkeys"]


class Kill:
    def sleep(self, s):
        pass


class Sim:
    """Game with a real toggle. `lost` = indexes of swap presses the game ignores."""

    def __init__(self, start=2, lost=(), blind=False, chicken_on=None):
        self.cfg = load_config()
        self.set, self.lost, self.blind, self.chicken_on = start, set(lost), blind, chicken_on
        self.swaps = 0
        self.selected = None
        self.casts = []
        self.failures = []
        self.hp = self.mp = 100
        self.kill = Kill()
        self.capture = self
        self.input = self

    def press(self, key):
        if key == HK["swap_weapons"]:
            if self.swaps not in self.lost:
                self.set = 3 - self.set
            self.swaps += 1
        elif key in (HK["skills"]["battle_orders"], HK["skills"]["battle_command"]):
            if self.set == 1:  # the skills only exist on the Call to Arms set
                self.selected = key
        else:
            self.selected = key

    def click(self, x, y, button="left", hover=0.08):
        self.casts.append((self.selected, self.set))
        if self.chicken_on == len(self.casts):
            raise Chicken("HP low")

    def sleep(self, s):
        pass

    def clock(self):
        return 1000.0

    def move(self, x, y):
        pass

    def grab(self):
        if self.blind:
            return MAIN_FRAME * 0
        return CTA_FRAME if self.set == 1 else MAIN_FRAME

    def save_failure(self, note):
        self.failures.append(note)


BC, BO = HK["skills"]["battle_command"], HK["skills"]["battle_orders"]


def test_clean_cast_ends_on_main_with_both_cries():
    bot = Sim()
    cast_warcries(bot)
    assert bot.set == 2 and bot.casts == [(BC, 1), (BO, 1)]
    assert bot.weapons_dirty is False and bot.warcries_at == 1000.0
    assert bot.selected == HK["skills"]["teleport"]


def test_lost_swap_to_the_flail_is_retried_before_casting():
    bot = Sim(lost=[0])
    cast_warcries(bot)
    assert bot.set == 2 and bot.casts == [(BC, 1), (BO, 1)]
    assert bot.weapons_dirty is False and bot.warcries_at == 1000.0


def test_lost_swap_back_is_retried():
    bot = Sim(lost=[1])
    cast_warcries(bot)
    assert bot.set == 2 and bot.casts == [(BC, 1), (BO, 1)] and bot.weapons_dirty is False


def test_starting_on_the_flail_still_casts_and_ends_on_main():
    bot = Sim(start=1)
    cast_warcries(bot)
    assert bot.set == 2 and bot.casts == [(BC, 1), (BO, 1)] and bot.weapons_dirty is False


def test_every_swap_lost_does_not_claim_a_cast():
    bot = Sim(lost=range(20))
    cast_warcries(bot)
    assert bot.set == 2 and bot.casts == []  # no Teleports at her own feet on the wrong set
    assert not hasattr(bot, "warcries_at")
    assert bot.weapons_dirty is False  # the read says she is on the main set


def test_chicken_mid_cast_leaves_the_flag_for_the_next_game():
    bot = Sim(chicken_on=1)
    with pytest.raises(Chicken):
        cast_warcries(bot)
    assert bot.weapons_dirty is True
    assert bot.set == 2  # the swap back still went out
    ensure_main_weapons(bot)
    assert bot.weapons_dirty is False


def test_unreadable_tabs_keep_the_flag():
    bot = Sim(blind=True)
    cast_warcries(bot)
    assert bot.casts == []
    assert bot.weapons_dirty is True and bot.failures == ["weapon_set_unknown"]
    assert bot.selected == HK["skills"]["teleport"]


def test_game_start_check_swaps_back_only_when_needed():
    bot = Sim(start=1)
    ensure_main_weapons(bot)
    assert bot.set == 2 and bot.swaps == 1 and bot.weapons_dirty is False
    bot = Sim()
    ensure_main_weapons(bot)
    assert bot.set == 2 and bot.swaps == 0


def test_loot_sign_ignores_white_and_what_was_already_there():
    from bot.meph import loot_labels, new_labels

    cfg = load_config()
    loot = Path(__file__).resolve().parent.parent / "fixtures" / "loot"
    rune = loot_labels(cv2.imread(str(loot / "pick_rune_1027-001135_685_329_37_13.png")), cfg)
    assert [a for a in rune if a.kind == "rune"]
    assert new_labels(rune, []) == rune
    assert new_labels(rune, rune) == []
    assert [a for a in loot_labels(cv2.imread(str(loot / "key_and_gold.png")), cfg) if a.kind == "white"] == []
