"""a1town.esc_cleared: after an Esc, wait for the game menu to fade before anything presses Esc again."""
from types import SimpleNamespace

from bot import a1town
from bot.vision import inventory


def _bot(states):
    t = {"now": 0.0, "states": list(states)}

    def observe():
        return t["states"].pop(0) if len(t["states"]) > 1 else t["states"][0]

    bot = SimpleNamespace(clock=lambda: t["now"], observe=observe, frame=None,
                          kill=SimpleNamespace(sleep=lambda s: t.__setitem__("now", t["now"] + s)))
    return bot, t


def _quiet(monkeypatch):
    monkeypatch.setattr(a1town, "menu_up", lambda bot, f=None: False)
    monkeypatch.setattr(inventory, "inventory_open", lambda f: False)


def test_waits_out_a_slow_fade(monkeypatch):
    _quiet(monkeypatch)
    bot, t = _bot(["esc_menu"] * 4 + ["in_game"])  # 0.8 s of menu after the Esc: the old 0.5 s re-check pressed again
    assert a1town.esc_cleared(bot) and 0.9 < t["now"] < 1.1


def test_gives_up_after_the_timeout(monkeypatch):
    _quiet(monkeypatch)
    bot, t = _bot(["esc_menu"])
    assert a1town.esc_cleared(bot) is False and 2.0 <= t["now"] < 2.3
