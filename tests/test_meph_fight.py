"""Finding Mephisto and looting him, with the game faked."""
from types import SimpleNamespace

from bot import lk, meph


def fight_with_names(names):
    """`names`: search index -> name_bar result for that search."""
    f = meph.MephFight.__new__(meph.MephFight)
    f.searched = []

    def first_name(pts, dwell=0.06):
        f.searched.append(list(pts))
        return names.get(len(f.searched) - 1)

    f.first_name = first_name
    return f


def test_find_looks_wider_when_he_is_not_at_his_last_point():
    f = fight_with_names({1: ((480, 75), {"mephisto": True, "life": 0.5})})
    f.last = (400, 75)
    assert f.find_meph() == ((480, 75), 0.5)
    assert len(f.searched) == 2 and len(f.searched[1]) == meph.WIDER_POINTS
    assert (400, 75) in f.searched[1]  # nearest his last point first


def test_find_stops_at_the_first_search_that_shows_him():
    f = fight_with_names({0: ((400, 75), {"mephisto": True, "life": 0.5})})
    f.last = (400, 75)
    assert f.find_meph() == ((400, 75), 0.5)
    assert len(f.searched) == 1


def test_find_sweeps_the_whole_grid_when_his_point_is_unknown():
    f = fight_with_names({})
    f.last = None
    assert f.find_meph() is None
    assert f.searched == [meph.MEPH_GRID]


def test_another_name_doesnt_end_the_search():
    f = fight_with_names({0: ((400, 75), {"mephisto": False, "life": 0.5}),
                          1: ((480, 75), {"mephisto": True, "life": 0.4})})
    f.last = (400, 75)
    assert f.find_meph() == ((480, 75), 0.4)


def loot_fight(clear_first):
    calls = []
    bot = SimpleNamespace(hp=99, mp=99, cfg={"meph": {"clear_before_loot": clear_first}},
                          sleep=lambda s: calls.append(("sleep", s)), wait_still=lambda timeout: None,
                          save_failure=lambda name: None)
    return calls, SimpleNamespace(
        bot=bot, seen=(400, 75), retreat=(100, 180), since_ref=set(), say=lambda s: None, snap=lambda n: None,
        away=lambda dx, dy, wait=0: None, back_to=lambda: True, in_danger=lambda: False, names_near=lambda **k: [],
        clear=lambda limit: calls.append("clear"))


def test_loot_skips_the_clear_and_looks_once(monkeypatch):
    monkeypatch.setattr(meph, "DEATH_THROES_S", 0)
    monkeypatch.setattr(meph, "RECOVER_S", 0)
    monkeypatch.setattr(meph, "DROP_WAIT", 0)
    looks = []
    monkeypatch.setattr(lk, "loot", lambda bot, take_all=False: looks.append(1) or [])
    calls, fight = loot_fight(clear_first=False)
    assert meph.loot_meph(fight) == []
    assert "clear" not in calls
    assert len(looks) == 1


def test_loot_can_still_clear_first(monkeypatch):
    monkeypatch.setattr(meph, "DEATH_THROES_S", 0)
    monkeypatch.setattr(meph, "RECOVER_S", 0)
    monkeypatch.setattr(meph, "DROP_WAIT", 0)
    monkeypatch.setattr(lk, "loot", lambda bot, take_all=False: [])
    calls, fight = loot_fight(clear_first=True)
    meph.loot_meph(fight)
    assert "clear" in calls
