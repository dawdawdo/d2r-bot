"""Lifecycle logic against a simulated game that reacts to clicks/keys."""
import numpy as np
import pytest

from bot.config import load_config
from bot.controller import BotError, Controller
from bot.io import Input
from bot.io.fake import FakeCapture, FakeWindow
from bot.killswitch import KillSwitch, KillSwitchTripped
from bot.lifecycle import create_game, ensure_main_menu, save_and_exit


class SimGame(Input):
    """Fake game: is both the Input sink and the classifier."""

    def __init__(self, ui, state="main_menu", load_frames=2):
        self.ui = {tuple(v): k for k, v in ui.items()}
        self.state = state
        self.pending: list[str] = []
        self.load_frames = load_frames
        self.log: list[str] = []
        self.difficulty = None

    def classify(self, frame):
        if self.pending:
            return self.pending.pop(0)
        return self.state

    def _goto(self, state):
        self.pending = ["loading"] * self.load_frames
        self.state = state

    def click(self, x, y, button="left"):
        name = self.ui.get((x, y), f"({x},{y})")
        self.log.append(name)
        if self.state == "main_menu" and name == "play":
            self.state = "difficulty"
        elif self.state == "difficulty" and name.startswith("difficulty_"):
            self.difficulty = name.split("_", 1)[1]
            self._goto("in_game")
        elif self.state == "esc_menu" and name == "save_and_exit":
            self._goto("main_menu")

    def key_down(self, key):
        self.log.append(f"key:{key}")
        if key == "esc" and self.state == "in_game":
            self.state = "esc_menu"

    def key_up(self, key):
        pass

    def move(self, x, y):
        pass

    def release_all(self):
        pass


@pytest.fixture
def cfg(tmp_path):
    c = load_config()
    c["paths"]["failures"] = tmp_path / "failures"
    return c


def make_bot(cfg, game, window=None, kill=None, clock=None):
    kw = {"clock": clock} if clock else {}
    bot = Controller(window or FakeWindow(), FakeCapture([np.zeros((720, 1280, 3), np.uint8)]),
                     game, game, kill or KillSwitch(), cfg, **kw)
    bot.poll = 0
    return bot


def test_full_cycle_twenty_times(cfg):
    game = SimGame(cfg["ui"])
    bot = make_bot(cfg, game)
    for _ in range(20):
        create_game(bot, "hell")
        assert game.state == "in_game" and game.difficulty == "hell"
        save_and_exit(bot)
        assert game.state == "main_menu"
    assert game.log[:2] == ["play", "difficulty_hell"]


@pytest.mark.parametrize("start", ["in_game", "esc_menu", "main_menu", "difficulty"])
def test_ensure_main_menu_recovers(cfg, start):
    game = SimGame(cfg["ui"], state=start)
    bot = make_bot(cfg, game)

    def key_down(key, _orig=game.key_down):
        _orig(key)
        if key == "esc" and game.state == "difficulty":
            game.state = "main_menu"

    game.key_down = key_down
    ensure_main_menu(bot)
    assert game.state == "main_menu"


def test_create_game_refuses_when_in_game(cfg):
    bot = make_bot(cfg, SimGame(cfg["ui"], state="in_game"))
    with pytest.raises(BotError):
        create_game(bot)


class TickClock:
    def __init__(self, step=1.0):
        self.t = 0.0
        self.step = step

    def __call__(self):
        self.t += self.step
        return self.t


def test_wait_for_timeout_saves_failure_frame(cfg):
    game = SimGame(cfg["ui"], state="unknown")
    bot = make_bot(cfg, game, clock=TickClock(5.0))
    bot.kill.sleep = lambda s: None
    with pytest.raises(BotError, match="timeout"):
        bot.wait_for("main_menu", 20)
    assert list(cfg["paths"]["failures"].glob("*.png"))


def test_no_input_when_window_not_foreground(cfg):
    class Background(FakeWindow):
        def is_foreground(self):
            return False

    game = SimGame(cfg["ui"])
    bot = make_bot(cfg, game, window=Background(), clock=TickClock(5.0))
    bot.kill.sleep = lambda s: None
    with pytest.raises(BotError, match="foreground"):
        bot.click_ui("play")
    assert game.log == []


def test_kill_switch_stops_lifecycle(cfg):
    kill = KillSwitch()
    kill.trip("test")
    game = SimGame(cfg["ui"])
    with pytest.raises(KillSwitchTripped):
        create_game(make_bot(cfg, game, kill=kill))
    assert game.log == []
