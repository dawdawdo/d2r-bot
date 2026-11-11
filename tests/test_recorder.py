import random
import numpy as np

from bot.recorder import DangerRecorder, FrameSampler


class SyncWriter:
    def put(self, job):
        job()


def frame():
    return np.zeros((720, 1280, 3), np.uint8)


def test_sampler_interval_and_cap(tmp_path):
    t = [1_800_000_000.0]
    s = FrameSampler(tmp_path, every_s=10, daily_cap=2, writer=SyncWriter(), clock=lambda: t[0])
    for _ in range(50):
        s.tick(frame(), "a3")
        t[0] += 1
    files = list(tmp_path.rglob("*.jpg"))
    assert len(files) == 2  # 50 s at 10 s -> 5 wanted, capped at 2


def test_danger_dump_on_sharp_drop_once(tmp_path):
    t = [1_800_000_000.0]
    r = DangerRecorder(tmp_path, writer=SyncWriter(), clock=lambda: t[0], calm_p=0, rng=random.Random(1))
    hp = 100.0
    for i in range(40):  # 4 s calm, then -40 over 1 s
        if i >= 30:
            hp -= 4
        r.tick(frame(), hp, 100)
        t[0] += 0.1
    dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
    assert len(dirs) == 1 and "_drop" in dirs[0].name
    assert (dirs[0] / "vitals.csv").exists() and len(list(dirs[0].glob("*.jpg"))) >= 7


def test_chicken_event_and_reset(tmp_path):
    t = [1_800_000_000.0]
    r = DangerRecorder(tmp_path, writer=SyncWriter(), clock=lambda: t[0], calm_p=0)
    r.event("chicken")  # nothing buffered yet: no dump
    assert not list(tmp_path.iterdir())
    for _ in range(10):
        r.tick(frame(), 80, 50)
        t[0] += 0.1
    r.event("chicken", "a3")
    assert any("_chicken_a3" in d.name for d in tmp_path.iterdir())
    r.reset()
    assert not r.vitals and not r.frames
