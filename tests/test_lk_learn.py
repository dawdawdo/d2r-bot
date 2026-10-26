"""Learned chest positions: the median of where chests were really found replaces the scouted spot."""
import bot.lk as lk


def test_learned_median_overrides_scouted(tmp_path, monkeypatch):
    monkeypatch.setattr(lk, "ROOT", tmp_path)
    (tmp_path / "maps" / "m").mkdir(parents=True)
    route = {"name": "m"}
    t = {"name": "hut", "chests_world": [[100, 100]]}
    learned = lk.load_learned(route)
    assert lk.chest_world(t, 0, learned) == (100, 100)
    for w in [(150, 90), (152, 95), (90, 160), (900, 900)]:  # one wild find is not learned
        lk.learn_chest(route, learned, t, 0, w)
    assert lk.chest_world(t, 0, lk.load_learned(route)) == (150, 95)
    assert len(learned["hut"]["0"]) == 3


def test_learned_keeps_last_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(lk, "ROOT", tmp_path)
    (tmp_path / "maps" / "m").mkdir(parents=True)
    route, t, learned = {"name": "m"}, {"name": "hut", "chests_world": [[0, 0]]}, {}
    for k in range(20):
        lk.learn_chest(route, learned, t, 0, (k, -k))
    assert len(learned["hut"]["0"]) == lk.LEARN_KEEP


def test_bonfire_layout_matches_scouted_chests():
    """The shared layout reproduces every chest found by scouting (within the search radius)."""
    import numpy as np

    east = lk.bonfire_targets({"name": "east", "world": [1629, 776]})
    west = lk.bonfire_targets({"name": "west", "world": [-2208, -389]})
    found = {"east_nw": (1046, 494), "east_nw_deep": (670, 399), "east_ne": (2479, 442),
             "west_nw": (-2765, -669), "west_ne": (-1376, -709)}
    for t in east + west:
        if t["name"] in found:
            assert np.hypot(*np.subtract(t["chests_world"][0], found[t["name"]])) < 60, t["name"]
    assert [t["name"] for t in west] == ["west_nw", "west_nw_deep", "west_ne"]
