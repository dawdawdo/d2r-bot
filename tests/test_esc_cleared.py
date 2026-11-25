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


def test_free_cells_closes_the_inventory_checked(monkeypatch):
    from bot import town

    calls = []
    bot = SimpleNamespace(cfg={"hotkeys": {"inventory": "i"}}, press=lambda k: calls.append(("press", k)),
                          kill=SimpleNamespace(sleep=lambda s: None))
    monkeypatch.setattr(town, "_scan_inventory", lambda b, wait_open: {"empty": [(0, 0), (1, 0)]})
    monkeypatch.setattr(town, "inventory_panel", lambda b, want_open: calls.append(("panel", want_open)) or True)
    assert town.free_cells(bot) == 2
    assert calls == [("press", "i"), ("panel", False)]  # one toggle to open; the close is checked, not blind


def test_clear_panels_closes_each_panel_that_is_up(monkeypatch):
    from bot import town

    calls = []
    bot = SimpleNamespace(press=lambda k: calls.append(("press", k)), observe=lambda: "esc_menu")
    monkeypatch.setattr(town, "stash_shown", lambda b: True)
    monkeypatch.setattr(town, "close_stash", lambda b: calls.append("close_stash") or True)
    monkeypatch.setattr(town, "inventory_panel", lambda b, want_open: calls.append(("panel", want_open)) or True)
    monkeypatch.setattr(a1town, "esc_cleared", lambda b: calls.append("esc_cleared") or True)
    town.clear_panels(bot)
    assert calls == ["close_stash", ("panel", False), ("press", "esc"), "esc_cleared"]


def test_clear_panels_with_nothing_up_presses_nothing(monkeypatch):
    from bot import town

    calls = []
    bot = SimpleNamespace(press=lambda k: calls.append(("press", k)), observe=lambda: "in_game")
    monkeypatch.setattr(town, "stash_shown", lambda b: False)
    monkeypatch.setattr(town, "inventory_panel", lambda b, want_open: True)
    town.clear_panels(bot)
    assert calls == []  # a blind Esc would open the game menu
