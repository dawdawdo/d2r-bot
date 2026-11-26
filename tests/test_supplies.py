"""A dry rejuv stash sends boss sessions to LK until it's stocked again (2026-11-05: 8 hours on an empty belt)."""
import pytest

from bot import state, supplies

CFG = {"town": {"refill_rejuvs": 40}, "game": {"players": 7, "meph_players": 1}}


@pytest.fixture(autouse=True)
def state_file(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "PATH", tmp_path / "state.json")


class T:
    def __init__(self, name):
        self.name = name


def test_two_zero_restocks_mean_dry_even_with_potions_showing():
    assert supplies.restocked(0, slots_gone=False) is False
    assert not state.load().get("stash_rejuvs_empty")
    assert supplies.restocked(0, slots_gone=False) is True
    assert state.load()["stash_rejuvs_empty"] is True


def test_a_good_restock_resets_the_count():
    supplies.restocked(0, False)
    supplies.restocked(5, False)
    assert supplies.restocked(0, False) is False


def test_both_stacks_gone_is_dry_at_once():
    assert supplies.restocked(0, slots_gone=True) is True


def test_going_dry_clears_a_stale_full_flag():
    state.save({"rejuv_stash_full": True})
    supplies.restocked(0, slots_gone=True)
    assert state.load()["rejuv_stash_full"] is False


def test_boss_session_farms_lk_until_the_target_then_resumes():
    meph, lk = [T("meph")], [T("lk")]
    assert supplies.tasks_for_run(meph, lk, CFG) is meph
    supplies.restocked(0, slots_gone=True)
    assert supplies.tasks_for_run(meph, lk, CFG) is lk
    assert state.load()["refill_left"] == 40

    state.save(supplies.after_stowing(state.load(), 15, False))
    assert state.load()["refill_left"] == 25
    assert state.load()["stash_rejuvs_empty"] is True  # LK must not drink what it's saving
    assert supplies.tasks_for_run(meph, lk, CFG) is lk

    state.save(supplies.after_stowing(state.load(), 25, False))
    assert "refill_left" not in state.load() and "stash_rejuvs_empty" not in state.load()
    assert supplies.tasks_for_run(meph, lk, CFG) is meph


def test_a_full_stack_ends_the_refill():
    st = supplies.after_stowing({"stash_rejuvs_empty": True, "refill_left": 30}, 2, True)
    assert "refill_left" not in st and "stash_rejuvs_empty" not in st


def test_outside_a_refill_any_stowed_rejuv_clears_the_flag():
    assert "stash_rejuvs_empty" not in supplies.after_stowing({"stash_rejuvs_empty": True}, 1, False)
    assert supplies.after_stowing({"stash_rejuvs_empty": True}, 0, False)["stash_rejuvs_empty"] is True


def test_lk_only_session_stays_lk():
    lk = [T("lk")]
    supplies.restocked(0, slots_gone=True)
    assert supplies.tasks_for_run(lk, [], CFG) is lk


def test_refill_can_be_switched_off():
    meph, lk = [T("meph")], [T("lk")]
    supplies.restocked(0, slots_gone=True)
    assert supplies.tasks_for_run(meph, lk, {"town": {"refill_rejuvs": 0}}) is meph


def test_session_start_rechecks_the_stash_but_a_refill_goes_on():
    state.save({"stash_rejuvs_empty": True, "refill_left": 12, "restock_zero": 1, "keys_left": 9})
    supplies.new_session()
    assert state.load() == {"keys_left": 9, "refill_left": 12}
    assert supplies.refilling({"town": {"refill_rejuvs": 40}})


def test_players_follow_the_tasks():
    assert supplies.players_for([T("meph")], CFG) == 1
    assert supplies.players_for([T("lk")], CFG) == 7
    assert supplies.players_for([T("lk"), T("meph")], CFG) == 7


def test_a_full_stack_does_not_mean_a_full_stash():
    from bot import supplies

    gem, rejuv, amulet = (0, 0), (1, 0), (2, 0)
    assert supplies.needs_a_page([gem, rejuv], {rejuv}, {gem}) == []
    assert supplies.needs_a_page([gem, amulet], {rejuv}, {gem}) == [amulet]


def test_only_refill_runs_save_rejuvs():
    meph, lk = ["meph"], ["lk"]
    cfg = {"town": {}}
    assert supplies.saving_rejuvs(lk, lk, cfg)
    assert not supplies.saving_rejuvs(meph, lk, cfg)  # a boss run drinks
    assert not supplies.saving_rejuvs(lk, [], cfg)  # an LK-only session has no refill
    assert not supplies.saving_rejuvs(lk, lk, {"town": {"refill_no_potions": False}})


def test_lk_only_session_saves_rejuvs_while_the_stash_is_dry():
    """features.save_rejuvs (2026-11-20): LK alone drank twice what it found; with the stash dry, no drinking."""
    lk, meph = [T("lk")], [T("meph")]
    cfg = {"town": {"lk_save_rejuvs": 20}}
    assert not supplies.saving_rejuvs(lk, [], cfg)  # the stash isn't known to be dry yet
    supplies.restocked(0, slots_gone=True)
    assert supplies.saving_rejuvs(lk, [], cfg)
    assert state.load()["refill_left"] == 20
    assert not supplies.saving_rejuvs(meph, [], cfg)
    assert not supplies.saving_rejuvs(lk, [], {"town": {"lk_save_rejuvs": 0}})
    state.save(supplies.after_stowing(state.load(), 20, stack_full=False))
    assert not supplies.saving_rejuvs(lk, [], cfg)  # 20 stashed: she drinks again


def test_full_stash_keeps_spares_off_until_restocks_take_it_below_the_margin(monkeypatch):
    """Stephen 2026-11-26: completely full on rejuvs, stop filling up. A restock used to re-arm spares at 98."""
    monkeypatch.setattr(supplies, "stash_rejuvs", lambda cfg: 99)
    supplies.new_session({"paths": {}})
    assert state.load()["rejuv_stash_full"] is True
    supplies.restocked(4, False)
    assert state.load()["rejuv_stash_count"] == 95 and state.load()["rejuv_stash_full"] is True
    for _ in range(4):
        supplies.restocked(4, False)
    assert state.load()["rejuv_stash_count"] == 79 and state.load()["rejuv_stash_full"] is False


def test_stowing_counts_up_and_a_stuck_rejuv_means_99():
    st = supplies.after_stowing({"rejuv_stash_count": 78, "rejuv_stash_full": False}, 3, False)
    assert st["rejuv_stash_count"] == 81 and st["rejuv_stash_full"] is True
    st = supplies.after_stowing({"rejuv_stash_count": 40}, 0, True)
    assert st["rejuv_stash_count"] == 99 and st["rejuv_stash_full"] is True


def test_a_low_stash_at_session_start_allows_spares(monkeypatch):
    state.save({"rejuv_stash_full": True})
    monkeypatch.setattr(supplies, "stash_rejuvs", lambda cfg: 50)
    supplies.new_session({"paths": {}})
    assert state.load()["rejuv_stash_full"] is False


def test_unknown_count_keeps_the_old_behaviour(monkeypatch):
    monkeypatch.setattr(supplies, "stash_rejuvs", lambda cfg: None)
    state.save({"rejuv_stash_full": True})
    supplies.new_session({"paths": {}})
    supplies.restocked(2, False)
    assert state.load()["rejuv_stash_full"] is False  # no count: room again, as before


def test_zero_restocks_with_plenty_counted_are_not_dry():
    """2026-11-26 14:21: two zero restocks called a stash with 79 rejuvs dry; LK runs went on with an empty belt."""
    state.save({"rejuv_stash_count": 79})
    assert supplies.restocked(0, slots_gone=False) is False
    assert supplies.restocked(0, slots_gone=False) is False
    assert not state.load().get("stash_rejuvs_empty")
    state.save({"rejuv_stash_count": 3})
    supplies.restocked(0, slots_gone=False)
    assert supplies.restocked(0, slots_gone=False) is True  # few left: believe it
