"""Automap odometry on live Durance 2 frames (2026-10-28): arrival, then hops (300, 0), (300, 0),
(0, -200) commanded. The screen odometer read the last one as blocked; the automap shows she went
up-left (wall in the way)."""
from pathlib import Path

import cv2
import numpy as np

from bot.durance import AutomapOdometer, StopGraph, automap_shown, frontier, view_mask

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "durance"


def frames():
    return [cv2.imread(str(FIX / f"automap_m{i}.png")) for i in range(4)]


def test_automap_is_seen():
    assert all(automap_shown(f) for f in frames())
    assert not automap_shown(cv2.imread(str(FIX / "hop_up_before.png")))  # no Tab: plain view


def test_hops_measured_from_the_automap():
    f = frames()
    odo = AutomapOdometer(f[0])
    moves = [odo.update(fr, expect=e) for fr, e in zip(f[1:], [(300, 0), (300, 0), (0, -200)])]
    assert not odo.lost
    m = np.array(moves)
    assert 250 < m[0][0] < 330 and abs(m[0][1]) < 40   # screen odometer: (287, -28)
    assert 120 < m[1][0] < 220 and abs(m[1][1]) < 70   # screen odometer: +173
    assert m[2][0] < -120 and m[2][1] < -60            # up-left, not "blocked"


def test_absolute_fix_after_a_jump(tmp_path):
    """A saved canvas + a later view: found again without a hop history (the next game)."""
    f = frames()
    odo = AutomapOdometer(f[0])
    for fr, e in zip(f[1:], [(300, 0), (300, 0), (0, -200)]):
        odo.update(fr, expect=e)
    odo.save(tmp_path)
    again = AutomapOdometer.load(tmp_path, f[0])
    assert np.hypot(*again.pos) < 20
    assert again.relocate(f[2], [(400, 0)])
    assert abs(again.pos[0] - odo_pos_after(f)) < 40


def odo_pos_after(f):
    odo = AutomapOdometer(f[0])
    odo.update(f[1], expect=(300, 0))
    odo.update(f[2], expect=(300, 0))
    return odo.pos[0]


def test_stop_graph_paths(tmp_path):
    g = StopGraph()
    a = g.add_stop((400, 0))
    b = g.add_stop((800, 0))
    g.link(0, a)
    g.link(a, b)
    assert g.path(0, b) == [0, a, b]
    assert g.nearest((790, 30)) == b and g.nearest((600, 0)) is None
    g.save(tmp_path / "g.json")
    assert StopGraph.load(tmp_path / "g.json").path(b, 0) == [b, a, 0]


def test_frontier_is_away_from_stops():
    odo = AutomapOdometer(frames()[0])
    g = StopGraph()
    assert all(np.hypot(*t) >= 600 for t in frontier(odo, g))


def test_firelight_is_not_automap():
    """Live 2026-10-28: braziers and lit floor share the automap's tan; as solid areas they're dropped
    (they filled the canvas and broke the fix). Before the blob filter: 15402 px."""
    from bot.durance import automap_pixels

    assert automap_pixels(cv2.imread(str(FIX / "firelight.png"))).sum() < 5000
    assert automap_pixels(frames()[0]).sum() > 4500  # thin lines untouched


def test_canvas_averages_out_one_off_noise():
    f = frames()
    odo = AutomapOdometer(f[0])
    x, y = np.round(odo._tl((0, 0))).astype(int)
    speck = np.zeros_like(view_mask(f[0]))
    speck[200, 100] = 1.0  # a torch flicker: one hit, then gone for the next four views
    odo._add(speck, (0, 0))
    for _ in range(4):
        odo._add(np.zeros_like(speck), (0, 0))
    assert odo.canvas[y + 200, x + 100] < 0.3


def test_newly_revealed_walls_count_fully():
    """The automap shows a place only after she's been near: dark views before that don't dilute it."""
    f = frames()
    odo = AutomapOdometer(f[0])
    x, y = np.round(odo._tl((0, 0))).astype(int)
    blank = np.zeros_like(view_mask(f[0]))
    for _ in range(10):
        odo._add(blank, (0, 0))
    m = blank.copy()
    m[200, 100] = 1.0
    odo._add(m, (0, 0))
    assert odo.canvas[y + 200, x + 100] > 0.9
