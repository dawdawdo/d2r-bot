from bot.learn import CELL, Explorer, _path_len, plan_route
from bot.lk import BONFIRE_LAYOUT


def test_frontier_grows_from_start():
    ex = Explorer()
    ex.mark_visited((0, 0))
    assert len(ex.frontier()) == 8
    assert ex.next_target((10, 0)) in [(CELL[0], 0.0), (-CELL[0], 0.0), (0.0, CELL[1]), (0.0, -CELL[1])]


def test_failed_cells_drop_out():
    ex = Explorer()
    ex.mark_visited((0, 0))
    for _ in range(2):
        ex.fail((CELL[0], 0))
    assert (1, 0) not in ex.frontier()


def test_fires_merge_and_skip_waypoint():
    ex = Explorer()
    ex.add_fires((0, 0), [(700, 360, 900)])            # 60 px from the WP: its brazier
    ex.add_fires((1430, 670), [(840, 430, 900)])       # world (1630, 770)
    ex.add_fires((1200, 900), [(1070, 200, 1000)])     # world (1630, 770) again
    ex.add_fires((-2200, -400), [(840, 330, 700)])     # seen once
    ex.add_fires((900, 900), [(660, 300, 900)])        # on the character: her own glow
    for _ in range(5):                                 # a fight: many sightings from one spot
        ex.add_fires((-3100, 700), [(830, 230, 900)])
    assert ex.bonfires() == [(1630, 770)]
    assert len(ex.bonfires(min_seen=1)) == 3  # incl. the fight flames, seen from one cell only


def test_roundtrip():
    ex = Explorer()
    ex.mark_visited((0, 0))
    ex.fail((400, 0))
    ex.add_fires((1600, 700), [(670, 400, 900)])
    back = Explorer.from_dict(ex.to_dict())
    assert back.visited == ex.visited and back.fails == ex.fails and back.fires == ex.fires


def test_plan_is_shortest_and_complete():
    camps = plan_route([(-2208, -389), (1629, 776)], BONFIRE_LAYOUT)
    assert [c["world"] for c in camps] == [[1629, 776], [-2208, -389]]  # east camp first, as by hand
    assert all(sorted(c["order"]) == sorted(BONFIRE_LAYOUT) for c in camps)
    assert camps[0]["order"] == ["nw_deep", "nw", "ne"]  # 770 px shorter than the hand order


def test_path_len():
    assert _path_len((0, 0), [(3, 4), (3, 0)]) == 9
