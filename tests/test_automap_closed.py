"""town.automap_closed: the Kurast Docks walk waits for the automap to go away (Proton closes it late)."""
from types import SimpleNamespace

from bot import durance, town


def _bot(open_for: int):
    """map_text_open reads True for the first `open_for` grabs, then False."""
    t = {"now": 0.0, "grabs": 0, "keys": []}

    def grab():
        t["grabs"] += 1
        return t["grabs"]

    bot = SimpleNamespace(clock=lambda: t["now"], press=lambda k: t["keys"].append(k),
                          kill=SimpleNamespace(sleep=lambda s: t.__setitem__("now", t["now"] + s)),
                          capture=SimpleNamespace(grab=grab))
    return bot, t


def test_closed_at_once(monkeypatch):
    bot, t = _bot(0)
    monkeypatch.setattr(durance, "map_text_open", lambda f: False)
    assert town.automap_closed(bot) and t["keys"] == [] and t["now"] < 0.2


def test_waits_for_a_late_close(monkeypatch):
    bot, t = _bot(5)
    monkeypatch.setattr(durance, "map_text_open", lambda f: f <= 5)
    assert town.automap_closed(bot) and t["keys"] == []
    assert 0.8 < t["now"] < 1.0  # six polls of 0.15 s


def test_still_up_presses_tab_once_more(monkeypatch):
    bot, t = _bot(0)
    state = {"open": True}
    monkeypatch.setattr(durance, "map_text_open", lambda f: state["open"])
    bot.press = lambda k: (t["keys"].append(k), state.update(open=False))
    assert town.automap_closed(bot) and t["keys"] == ["tab"]


def test_gives_up_after_two_tries(monkeypatch):
    bot, t = _bot(0)
    monkeypatch.setattr(durance, "map_text_open", lambda f: True)
    assert town.automap_closed(bot) is False and t["keys"] == ["tab", "tab"]
