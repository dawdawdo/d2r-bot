import json

import pytest

from bot import supervisor as sv


class FakeProc:
    def __init__(self, code):
        self.returncode, self.pid = code, 1

    def poll(self):
        return self.returncode


@pytest.fixture
def sup(tmp_path, monkeypatch):
    monkeypatch.setattr(sv, "DESIRED", tmp_path / "desired.json")
    monkeypatch.setattr(sv, "BOT_OUT", tmp_path / "bot.out")
    monkeypatch.setattr(sv.control, "read_status", lambda: {})
    import bot.io

    closed = []
    monkeypatch.setattr(bot.io, "close_game", lambda: closed.append(1) or True)  # never the real game in tests
    s = sv.Supervisor({})
    s.closed = closed
    s.started = sv.time.time() - 1000
    sv.write_desired(run=True, tasks="meph")
    return s


def end_with(s, out, code):
    sv.BOT_OUT.write_text(out)
    s.out_offset, s.proc = 0, FakeProc(code)
    s.ended()


def test_f12_stays_stopped(sup):
    end_with(sup, "run 1/150 ok in 150s\nstopped by kill switch: F12 pressed\n", 1)
    assert sv.read_desired()["run"] is False and sup.state == "stopped"


def test_normal_end_restarts(sup):
    end_with(sup, "run 150/150 ok\n140/150 runs ok\n", 1)
    assert sv.read_desired()["run"] is True and sup.state == "idle" and sup.fails == 0
    assert sup.closed == [1]  # D2R closed so the next session starts it fresh (memory growth)


def test_game_stays_open_after_stop_f12_or_mouse_trip(sup):
    end_with(sup, "stopped by kill switch: F12 pressed\n", 1)
    end_with(sup, "run 3/150 ok\nstop requested (web page); not starting run 4\n", 0)
    end_with(sup, "stopped by mouse trip: mouse moved by user (TouchPad)\n", 1)
    assert sup.closed == []


def test_fail_streak_backs_off_and_doubles(sup):
    end_with(sup, "run 1/150 fail\nERROR 4 failures in a row; stopping\n", 1)
    first = sup.backoff_until - sv.time.time()
    sup.started = sv.time.time() - 1000
    end_with(sup, "run 1/150 fail\nERROR 4 failures in a row; stopping\n", 1)
    assert sup.state == "backoff" and sup.fails == 2
    assert sup.backoff_until - sv.time.time() > first * 1.5


def test_quick_death_counts_as_failure(sup):
    sup.started = sv.time.time() - 30
    end_with(sup, "ERROR D2R didn't start\n", 1)
    assert sup.state == "backoff"


def test_remote_reply_sets_desired(sup, monkeypatch):
    sup.remote_url = "https://example.invalid/hook"

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"desired": {"run": False, "tasks": "lk"}}).encode()

    monkeypatch.setattr(sv.urllib.request, "urlopen", lambda req, timeout: Resp())
    monkeypatch.setattr(sv, "tail_csv", lambda p, n: [])
    sup.remote()
    d = sv.read_desired()
    assert d["run"] is False and d["tasks"] == "lk" and d["set_by"] == "remote"


def test_f12_on_a_session_started_elsewhere(sup, monkeypatch):
    later = sv.time.time() + 5
    monkeypatch.setattr(sv.control, "read_status",
                        lambda: {"state": "idle", "tally": {"kill switch": 1}, "updated": later})
    monkeypatch.setattr(sup, "remote", lambda: None)
    monkeypatch.setattr(sup, "write_status", lambda: None)
    started = []
    monkeypatch.setattr(sup, "start", lambda d: started.append(d))
    sup.tick()
    assert not started and sv.read_desired()["run"] is False


def test_new_tasks_restart_the_session_after_this_run(sup, monkeypatch):
    monkeypatch.setattr(sup, "remote", lambda: None)
    monkeypatch.setattr(sup, "write_status", lambda: None)
    monkeypatch.setattr(sup, "other_bot", lambda: False)
    asked = []
    monkeypatch.setattr(sup, "stop", lambda now: asked.append(now))
    sup.proc, sup.session = FakeProc(None), ("chests", "meph")
    sup.tick()
    assert asked == []  # same tasks: nothing to do
    sv.write_desired(tasks="lk")
    sup.tick()
    sup.tick()
    assert asked == [False]  # once, after the current run
    end_with(sup, "run 3/150 ok in 90s\nstop requested (web page); not starting run 4\n", 1)
    assert sv.read_desired()["run"] is True and sup.state == "idle"  # not "stopped": the next tick starts lk


def test_mouse_trip_waits_for_a_quiet_desktop(sup):
    end_with(sup, "run 85/150 ok\nstopped by mouse trip: mouse moved by user (TouchPad)\n", 1)
    assert sv.read_desired()["run"] is True and sup.state == "backoff"
    assert not sup.desk_quiet(lambda: 9999)          # the hold time hasn't passed
    sup.mouse_hold_until = sv.time.time() - 1
    assert not sup.desk_quiet(lambda: 30)            # someone touched it 30 s ago
    assert sup.desk_quiet(lambda: sv.MOUSE_QUIET_S + 1)
    assert sup.mouse_hold_until == 0 and sup.desk_quiet(lambda: 0)  # cleared: normal starts again


def test_f12_still_stays_stopped_when_a_mouse_trip_is_not_in_the_output(sup):
    end_with(sup, "stopped by kill switch: F12 pressed\n", 1)
    assert sv.read_desired()["run"] is False
