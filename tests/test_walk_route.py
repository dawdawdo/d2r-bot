"""town.walk_route: a late start (GLaDOS input lag) must not get a second click (it doubled the leg)."""
from types import SimpleNamespace

import numpy as np

from bot import nav, town


class _Odo:
    def __init__(self, frame):
        self.pos, self.lost = np.zeros(2), False

    def update(self, frame):
        return 0.0, 0.0


def _bot():
    clicks = []
    bot = SimpleNamespace(click=lambda x, y: clicks.append((x, y)), capture=SimpleNamespace(grab=lambda: None),
                          kill=SimpleNamespace(sleep=lambda s: None))
    return bot, clicks


def test_late_start_gets_one_click(monkeypatch):
    bot, clicks = _bot()
    seen = iter([False, True])  # still at the first look, moving 0.5 s later
    monkeypatch.setattr(nav, "Odometer", _Odo)
    monkeypatch.setattr(town, "_walk_settle", lambda b, o, **k: True)
    monkeypatch.setattr(town, "_view_moved", lambda a, b: next(seen))
    town.walk_route(bot, [(900, 300)])
    assert clicks == [(900, 300)]


def test_no_move_at_all_clicks_again(monkeypatch):
    bot, clicks = _bot()
    monkeypatch.setattr(nav, "Odometer", _Odo)
    monkeypatch.setattr(town, "_walk_settle", lambda b, o, **k: True)
    monkeypatch.setattr(town, "_view_moved", lambda a, b: False)
    town.walk_route(bot, [(900, 300)], retries=2)
    assert clicks == [(900, 300)] * 3
