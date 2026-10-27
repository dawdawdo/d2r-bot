import json

import pytest

from bot import control


@pytest.fixture
def tmp_control(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "CONTROL", tmp_path / "control.txt")
    monkeypatch.setattr(control, "STATUS", tmp_path / "status.json")
    return tmp_path


def test_run_module_imports():
    import bot.run  # noqa: F401  (a syntax error here once slipped past the other tests)


def test_stop_requests(tmp_control):
    assert control.read() is None
    control.request("after_run")
    assert control.read() == "after_run"
    control.request("now")
    assert control.read() == "now"
    control.clear()
    assert control.read() is None
    with pytest.raises(ValueError):
        control.request("later")


def test_status_roundtrip(tmp_control):
    assert control.read_status() == {"state": "idle"}
    control.write_status(state="running", run=3, runs=20, task="lk", tally={"ok": 2})
    st = control.read_status()
    assert st["state"] == "running" and st["run"] == 3 and st["tally"] == {"ok": 2} and "pid" in st
    json.loads((tmp_control / "status.json").read_text())


def test_controller_raises_stop_now_once(tmp_control):
    import numpy as np

    from bot.config import load_config
    from bot.controller import Controller
    from bot.io.fake import FakeCapture, FakeWindow
    from bot.killswitch import KillSwitch

    class Cls:
        def classify(self, frame):
            return "main_menu"

    t = [0.0]
    bot = Controller(FakeWindow(), FakeCapture([np.zeros((720, 1280, 3), np.uint8)]), None, Cls(), KillSwitch(),
                     load_config(), clock=lambda: t[0])
    bot.observe()
    control.request("now")
    t[0] += 2
    with pytest.raises(control.StopNow):
        bot.observe()
    t[0] += 2
    bot.observe()  # once only: the save & exit that follows must not be interrupted
